"""Multi-format document loader (TXT, PDF, DOCX, MD)"""
from pathlib import Path
from typing import List, Dict, Optional
from langchain.schema import Document
from langchain_community.document_loaders import (
 TextLoader,
 PyPDFLoader,
 Docx2txtLoader,
 UnstructuredMarkdownLoader,
)
from src.utils import logger, clean_text


class MultiFormatDocumentLoader:

    SUPPORTED_FORMATS = {
        '.txt': 'text',
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'docx',
        '.md': 'markdown',
        '.markdown': 'markdown',
    }

    def __init__(self):
        self.documents: List[Document] = []
        self.stats: Dict = {
            'total': 0,
            'by_format': {},
            'errors': []
        }

    def detect_format(self, file_path: Path) -> Optional[str]:
        suffix = file_path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(suffix)

    def load_text(self, file_path: Path) -> List[Document]:
        try:
            loader = TextLoader(str(file_path), encoding='utf-8')
            docs = loader.load()

            # Nettoyer et enrichir les métadonnées
            for doc in docs:
                doc.page_content = clean_text(doc.page_content)
                doc.metadata['format'] = 'text'
                doc.metadata['filename'] = file_path.name

            return docs
        except Exception as e:
            logger.error(f"Erreur chargement TXT {file_path.name}: {e}")
            return []

    def load_pdf(self, file_path: Path) -> List[Document]:
        try:
            loader = PyPDFLoader(str(file_path))
            docs = loader.load()

            # Nettoyer et enrichir les métadonnées
            for i, doc in enumerate(docs):
                doc.page_content = clean_text(doc.page_content)
                doc.metadata['format'] = 'pdf'
                doc.metadata['filename'] = file_path.name
                doc.metadata['page_number'] = i + 1

            return docs
        except Exception as e:
            logger.error(f"Erreur chargement PDF {file_path.name}: {e}")
            return []

    def load_docx(self, file_path: Path) -> List[Document]:
        try:
            loader = Docx2txtLoader(str(file_path))
            docs = loader.load()

            # Nettoyer et enrichir les métadonnées
            for doc in docs:
                doc.page_content = clean_text(doc.page_content)
                doc.metadata['format'] = 'docx'
                doc.metadata['filename'] = file_path.name

            return docs
        except Exception as e:
            logger.error(f"Erreur chargement DOCX {file_path.name}: {e}")
            return []

    def load_markdown(self, file_path: Path) -> List[Document]:
        try:
            loader = UnstructuredMarkdownLoader(str(file_path))
            docs = loader.load()

            # Nettoyer et enrichir les métadonnées
            for doc in docs:
                doc.page_content = clean_text(doc.page_content)
                doc.metadata['format'] = 'markdown'
                doc.metadata['filename'] = file_path.name

            return docs
        except Exception as e:
            logger.error(f"Erreur chargement MD {file_path.name}: {e}")
            return []

    def load_document(self, file_path: Path) -> List[Document]:
        format_type = self.detect_format(file_path)

        if not format_type:
            logger.warning(f"Format non supporté: {file_path.suffix} ({file_path.name})")
            return []

        logger.debug(f"Chargement {format_type.upper()}: {file_path.name}")

        # Dispatcher vers le bon loader
        loaders = {
            'text': self.load_text,
            'pdf': self.load_pdf,
            'docx': self.load_docx,
            'markdown': self.load_markdown,
        }

        loader_func = loaders.get(format_type)
        if not loader_func:
            logger.warning(f"Pas de loader pour {format_type}")
            return []

        return loader_func(file_path)

    def load_directory(self, directory: Path, recursive: bool = True) -> List[Document]:
        logger.section(f"CHARGEMENT MULTI-FORMAT: {directory}")

        all_docs = []
        pattern = "**/*" if recursive else "*"

        # Parcourir tous les fichiers
        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            format_type = self.detect_format(file_path)
            if not format_type:
                continue

            # Charger le document
            docs = self.load_document(file_path)

            if docs:
                all_docs.extend(docs)

                # Mettre à jour les stats
                self.stats['total'] += len(docs)
                self.stats['by_format'][format_type] = \
                    self.stats['by_format'].get(format_type, 0) + len(docs)

                logger.info(
                    f" {file_path.name} ({format_type.upper()}) "
                    f"→ {len(docs)} document(s)"
                )
            else:
                self.stats['errors'].append(file_path.name)

        # Afficher le résumé
        logger.info(f"\n Résumé du chargement:")
        logger.info(f" Total documents: {self.stats['total']}")
        logger.info(f" Par format:")
        for fmt, count in self.stats['by_format'].items():
            logger.info(f" - {fmt.upper()}: {count}")

        if self.stats['errors']:
            logger.warning(f" Erreurs: {len(self.stats['errors'])} fichiers")

        self.documents = all_docs
        return all_docs

    def get_stats(self) -> Dict:
        return self.stats
