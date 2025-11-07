"""Weaviate RAG Pipeline with Hybrid Search and Reranking"""

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
from typing import List, Dict, Optional
from pathlib import Path
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

from src.config import validate_config
from src.document_loader import MultiFormatDocumentLoader
from src.utils import logger


class WeaviateRAGPipeline:
    COLLECTION_NAME = "GivaudanDocument"

    def __init__(
        self,
        weaviate_url: str = "http://localhost:8090",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k_retrieve: int = 5,  # Get 5 candidates from hybrid search
        top_k_final: int = 3,
        hybrid_alpha: float = 0.7  # 70% dense vectors, 30% BM25
    ):
        validate_config()

        logger.info(" Initialisation Weaviate RAG Pipeline")

        # Configuration
        self.weaviate_url = weaviate_url
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k_retrieve = top_k_retrieve
        self.top_k_final = top_k_final
        self.hybrid_alpha = hybrid_alpha  # 0 = pure BM25, 1 = pure vector

        # Embeddings - BGE-large
        logger.info(" Loading BGE-large embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        # Cross-Encoder for reranking
        logger.info(" Loading Cross-Encoder...")
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]
        )

        # Weaviate client
        self.client = None
        self.collection = None

        # Connect to Weaviate
        self._connect_weaviate()

        logger.info(" Weaviate RAG Pipeline initialized")
        logger.info(f" - Weaviate URL: {weaviate_url}")
        logger.info(f" - Embeddings: BGE-large-en-v1.5")
        logger.info(f" - Hybrid alpha: {hybrid_alpha:.0%} dense")
        logger.info(f" - Reranker: CrossEncoder ms-marco-MiniLM")

    def _connect_weaviate(self):
        try:
            logger.info(f" Connecting to Weaviate at {self.weaviate_url}...")

            self.client = weaviate.connect_to_local(
                host=self.weaviate_url.replace("http://", "").split(":")[0],
                port=int(self.weaviate_url.split(":")[-1])
            )

            # Check if connected
            if self.client.is_ready():
                logger.info(f" Connected to Weaviate v{self.client.get_meta()['version']}")
            else:
                raise Exception("Weaviate not ready")

            # Create or get collection
            self._setup_schema()

        except Exception as e:
            logger.error(f" Failed to connect to Weaviate: {e}")
            raise

    def _setup_schema(self):
        logger.info(f"\n Setting up schema: {self.COLLECTION_NAME}")

        # Check if collection exists
        if self.client.collections.exists(self.COLLECTION_NAME):
            logger.info(f" Collection '{self.COLLECTION_NAME}' already exists")
            self.collection = self.client.collections.get(self.COLLECTION_NAME)
            return

        # Create collection with rich metadata schema
        logger.info(f" Creating collection '{self.COLLECTION_NAME}'...")

        self.collection = self.client.collections.create(
            name=self.COLLECTION_NAME,

            # Vector index configuration
            vectorizer_config=Configure.Vectorizer.none(),  # We provide embeddings

            # Enable BM25 for hybrid search
            inverted_index_config=Configure.inverted_index(
                bm25_b=0.75,
                bm25_k1=1.2
            ),

            # Metadata properties
            properties=[
                # Core content
                Property(name="content", data_type=DataType.TEXT,
                         description="Chunk content text"),

                # Document metadata
                Property(name="filename", data_type=DataType.TEXT,
                         description="Source filename"),
                Property(name="format", data_type=DataType.TEXT,
                         description="File format: pdf, txt, docx, md"),

                # Positional metadata
                Property(name="chunk_index", data_type=DataType.INT,
                         description="Chunk position in document"),
                Property(name="page_number", data_type=DataType.INT,
                         description="Page number (for PDFs)"),
            ]
        )

        logger.info(f" Collection '{self.COLLECTION_NAME}' created")
        logger.info(f" - Properties: 5 metadata fields")
        logger.info(f" - Hybrid search: enabled (BM25 + Dense)")

    def _extract_metadata(self, doc: Document, chunk_index: int, total_chunks: int) -> Dict:
        """Extract metadata from document"""
        metadata = {
            "content": doc.page_content,
            "filename": doc.metadata.get('filename', 'unknown'),
            "format": doc.metadata.get('format', 'unknown'),
            "chunk_index": chunk_index,
            "page_number": doc.metadata.get('page_number', 0),
        }
        return metadata

    def index_documents(self, data_dir: str = "data/raw"):
        """Load and index documents into Weaviate"""
        logger.info(f"\n{'='*80}")
        logger.info(" INDEXING DOCUMENTS TO WEAVIATE")
        logger.info('='*80)

        # Load documents
        logger.info(f" Loading documents from {data_dir}...")
        loader = MultiFormatDocumentLoader()
        documents = loader.load_directory(Path(data_dir), recursive=False)
        logger.info(f" Loaded {len(documents)} documents")

        # Chunk documents
        logger.info(f" Chunking documents (size: {self.chunk_size}, overlap: {self.chunk_overlap})...")
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f" Created {len(chunks)} chunks")

        # Generate embeddings and index
        logger.info(f" Generating embeddings and indexing to Weaviate...")

        indexed_count = 0
        batch_size = 10

        with self.collection.batch.dynamic() as batch:
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.embeddings.embed_query(chunk.page_content)

                # Extract rich metadata
                metadata = self._extract_metadata(chunk, i, len(chunks))

                # Add to Weaviate
                batch.add_object(
                    properties=metadata,
                    vector=embedding
                )

                indexed_count += 1

                if (i + 1) % batch_size == 0:
                    logger.info(f" → Indexed {i + 1}/{len(chunks)} chunks...")

        logger.info(f" Successfully indexed {indexed_count} chunks to Weaviate!")
        logger.info(f" - Collection: {self.COLLECTION_NAME}")
        logger.info(f" - Vector dimensions: 1024 (BGE-large)")
        logger.info(f" - Metadata fields: 5")

    def hybrid_search(self, query: str, k: int = None) -> List[Dict]:
        """
        Hybrid search (BM25 + Dense vectors)

        Args:
            query: Search query
            k: Number of results (default: top_k_retrieve)

        Returns:
            List of results with content and metadata
        """
        if k is None:
            k = self.top_k_retrieve

        logger.debug(f"[Weaviate Search] Query: {query}, K: {k}")

        # Generate query embedding
        query_vector = self.embeddings.embed_query(query)

        # Hybrid search (BM25 + Dense)
        response = self.collection.query.hybrid(
            query=query,
            vector=query_vector,
            alpha=self.hybrid_alpha,  # 0.7 = 70% dense, 30% BM25
            limit=k,
            return_metadata=MetadataQuery(score=True)
        )

        results = []
        for obj in response.objects:
            results.append({
                'content': obj.properties['content'],
                'metadata': {k: v for k, v in obj.properties.items() if k != 'content'},
                'score': obj.metadata.score if obj.metadata else 0.0
            })

        logger.debug(f" → Retrieved {len(results)} results")
        return results

    def retrieve_and_rerank(
        self,
        query: str,
        k: int = None,
        fast_mode: bool = False
    ) -> List[Document]:
        """
        Retrieve with hybrid search + optional cross-encoder reranking

        Args:
            query: Search query
            k: Final number of documents (default: top_k_final)
            fast_mode: Skip cross-encoder reranking for speed

        Returns:
            Reranked documents (or just hybrid search results if fast_mode=True)
        """
        if k is None:
            k = self.top_k_final

        logger.debug(f"[Weaviate Retrieve+Rerank] Query: {query} (fast_mode={fast_mode})")

        # Step 1: Hybrid search → Top results
        retrieve_k = k if fast_mode else self.top_k_retrieve
        results = self.hybrid_search(query, k=retrieve_k)

        if not results:
            logger.warning("No results from hybrid search")
            return []

        logger.debug(f" Step 1: Hybrid search → {len(results)} results")

        # FAST MODE: Skip cross-encoder reranking (saves 2-5 seconds!)
        if fast_mode:
            logger.debug(f" [FAST MODE] Skipping cross-encoder reranking")
            docs = []
            for i, result in enumerate(results[:k], 1):
                doc = Document(
                    page_content=result['content'],
                    metadata={**result['metadata'], 'hybrid_score': result['score']}
                )
                docs.append(doc)
                logger.debug(f" {i}. {result['metadata']['filename']} (hybrid score: {result['score']:.3f})")

            logger.info(f" Retrieved {len(docs)} documents (hybrid only - FAST)")
            return docs

        # STANDARD MODE: Cross-encoder reranking for maximum precision
        logger.debug(f" Step 2: Cross-encoder reranking → top {k}")

        # Prepare pairs
        pairs = [[query, result['content']] for result in results]

        # Score with cross-encoder
        scores = self.cross_encoder.predict(pairs)

        # Sort by score
        result_score_pairs = list(zip(results, scores))
        result_score_pairs.sort(key=lambda x: x[1], reverse=True)

        # Convert to Document objects
        reranked_docs = []
        for i, (result, score) in enumerate(result_score_pairs[:k], 1):
            doc = Document(
                page_content=result['content'],
                metadata={**result['metadata'], 'rerank_score': float(score)}
            )
            reranked_docs.append(doc)

            logger.debug(f" {i}. {result['metadata']['filename']} (score: {score:.3f})")

        logger.info(f" Retrieved {len(reranked_docs)} documents (hybrid + reranked)")
        return reranked_docs

    def retrieve_relevant_chunks(self, query: str, k: int = 3, fast_mode: bool = True) -> List[Document]:
        return self.retrieve_and_rerank(query, k=k, fast_mode=fast_mode)

    def get_stats(self) -> Dict:
        """Get collection statistics"""
        aggregate = self.collection.aggregate.over_all(total_count=True)

        return {
            'collection_name': self.COLLECTION_NAME,
            'total_chunks': aggregate.total_count,
            'weaviate_url': self.weaviate_url,
            'hybrid_alpha': self.hybrid_alpha,
            'top_k_retrieve': self.top_k_retrieve,
            'top_k_final': self.top_k_final
        }

    def close(self):
        """Close Weaviate connection"""
        if self.client:
            self.client.close()
            logger.info(" Weaviate connection closed")
