// ==================== CONFIGURATION ====================
const API_URL = 'http://localhost:8001';

// ==================== STATE ====================
let chatHistory = [];
let currentConversationId = null;
let lastResponseTime = null;
let lastCacheHit = false;

// ==================== DOM ELEMENTS ====================
const elements = {
    sidebar: document.getElementById('sidebar'),
    chatContainer: document.getElementById('chatContainer'),
    chatMessages: document.getElementById('chatMessages'),
    userInput: document.getElementById('userInput'),
    sendButton: document.getElementById('sendButton'),
    welcome: document.getElementById('welcome'),
    perfBadge: document.getElementById('perfBadge'),
    themeText: document.getElementById('themeText'),
    conversationHistory: document.getElementById('conversationHistory')
};

// ==================== INITIALIZATION ====================
function init() {
    // Load theme preference
    loadThemePreference();

    // Load conversation history
    loadConversationHistory();

    // Focus input
    elements.userInput.focus();

    // Check API health
    checkAPIHealth();
}

// ==================== THEME MANAGEMENT ====================
function loadThemePreference() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeUI(newTheme);
}

function updateThemeUI(theme) {
    const lightIcon = document.querySelector('.theme-icon-light');
    const darkIcon = document.querySelector('.theme-icon-dark');
    const themeText = elements.themeText;

    if (theme === 'dark') {
        lightIcon.style.display = 'none';
        darkIcon.style.display = 'block';
        themeText.textContent = 'Mode clair';
    } else {
        lightIcon.style.display = 'block';
        darkIcon.style.display = 'none';
        themeText.textContent = 'Mode sombre';
    }
}

// ==================== CONVERSATION HISTORY MANAGEMENT ====================
function loadConversationHistory() {
    const conversations = getConversations();
    displayConversationHistory(conversations);
}

function getConversations() {
    const saved = localStorage.getItem('givaudan_conversations');
    return saved ? JSON.parse(saved) : [];
}

function saveConversation() {
    if (!currentConversationId || chatHistory.length === 0) return;

    const conversations = getConversations();
    const existingIndex = conversations.findIndex(c => c.id === currentConversationId);

    const conversation = {
        id: currentConversationId,
        title: getConversationTitle(chatHistory),
        messages: chatHistory,
        timestamp: new Date().toISOString(),
        lastModified: Date.now()
    };

    if (existingIndex >= 0) {
        conversations[existingIndex] = conversation;
    } else {
        conversations.unshift(conversation);
    }

    // Keep only last 50 conversations
    const trimmed = conversations.slice(0, 50);
    localStorage.setItem('givaudan_conversations', JSON.stringify(trimmed));

    loadConversationHistory();
}

function getConversationTitle(messages) {
    // Get first user message as title (max 50 chars)
    const firstUserMsg = messages.find(m => m.role === 'user');
    if (firstUserMsg) {
        return firstUserMsg.content.substring(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '');
    }
    return 'Nouvelle conversation';
}

function displayConversationHistory(conversations) {
    if (!elements.conversationHistory) return;

    if (conversations.length === 0) {
        elements.conversationHistory.innerHTML = '<div class="no-conversations">Aucune conversation</div>';
        return;
    }

    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000;
    const oneWeek = 7 * oneDay;

    const today = [];
    const yesterday = [];
    const thisWeek = [];
    const older = [];

    conversations.forEach(conv => {
        const age = now - conv.lastModified;
        if (age < oneDay) {
            today.push(conv);
        } else if (age < 2 * oneDay) {
            yesterday.push(conv);
        } else if (age < oneWeek) {
            thisWeek.push(conv);
        } else {
            older.push(conv);
        }
    });

    let html = '';

    if (today.length > 0) {
        html += '<div class="conversation-group-title">Aujourd\'hui</div>';
        html += today.map(c => createConversationItem(c)).join('');
    }

    if (yesterday.length > 0) {
        html += '<div class="conversation-group-title">Hier</div>';
        html += yesterday.map(c => createConversationItem(c)).join('');
    }

    if (thisWeek.length > 0) {
        html += '<div class="conversation-group-title">Cette semaine</div>';
        html += thisWeek.map(c => createConversationItem(c)).join('');
    }

    if (older.length > 0) {
        html += '<div class="conversation-group-title">Plus ancien</div>';
        html += older.map(c => createConversationItem(c)).join('');
    }

    elements.conversationHistory.innerHTML = html;
}

function createConversationItem(conversation) {
    const isActive = conversation.id === currentConversationId ? 'active' : '';
    return `
        <div class="conversation-item ${isActive}" onclick="loadConversation('${conversation.id}')">
            <div class="conversation-title">${escapeHtml(conversation.title)}</div>
            <button class="delete-conversation" onclick="event.stopPropagation(); deleteConversation('${conversation.id}')" title="Supprimer">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    `;
}

function loadConversation(conversationId) {
    const conversations = getConversations();
    const conversation = conversations.find(c => c.id === conversationId);

    if (!conversation) return;

    currentConversationId = conversationId;
    chatHistory = conversation.messages;

    // Clear and reload messages
    elements.chatMessages.innerHTML = '';

    chatHistory.forEach(msg => {
        addMessage(msg.role, msg.content);
    });

    loadConversationHistory();

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        toggleSidebar();
    }
}

function deleteConversation(conversationId) {
    if (!confirm('Supprimer cette conversation ?')) return;

    let conversations = getConversations();
    conversations = conversations.filter(c => c.id !== conversationId);
    localStorage.setItem('givaudan_conversations', JSON.stringify(conversations));

    if (conversationId === currentConversationId) {
        newChat();
    }

    loadConversationHistory();
}

// ==================== SIDEBAR MANAGEMENT ====================
function toggleSidebar() {
    elements.sidebar.classList.toggle('active');
}

function newChat() {
    // Save current conversation if it exists
    if (currentConversationId && chatHistory.length > 0) {
        saveConversation();
    }

    // Create new conversation
    currentConversationId = 'conv_' + Date.now();
    chatHistory = [];

    // Clear messages
    elements.chatMessages.innerHTML = '';

    // Show welcome screen
    showWelcomeScreen();

    // Clear performance badge
    elements.perfBadge.innerHTML = '';

    // Reset input
    elements.userInput.value = '';
    autoResize(elements.userInput);
    elements.userInput.focus();

    // Update sidebar
    loadConversationHistory();
}

function showWelcomeScreen() {
    const welcomeHTML = `
        <div class="welcome" id="welcome">
            <div class="welcome-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </div>
            <h2>Bienvenue chez Givaudan</h2>
            <p>Je suis votre assistant IA spécialisé en parfumerie et arômes. Posez-moi vos questions sur Givaudan, nos produits, technologies et services.</p>

            <div class="example-prompts">
                <button class="example-prompt" onclick="askQuestion('Où se trouvent les laboratoires Givaudan ?')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                        <circle cx="12" cy="10" r="3"></circle>
                    </svg>
                    Où sont les laboratoires ?
                </button>
                <button class="example-prompt" onclick="askQuestion('Qu\\'est-ce que Myrissi ?')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    Qu'est-ce que Myrissi ?
                </button>
                <button class="example-prompt" onclick="askQuestion('Explique la pyramide olfactive')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                        <path d="M2 17l10 5 10-5M2 12l10 5 10-5"></path>
                    </svg>
                    La pyramide olfactive
                </button>
                <button class="example-prompt" onclick="askQuestion('Quels sont les principaux métiers de Givaudan ?')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                    Les métiers Givaudan
                </button>
            </div>
        </div>
    `;

    elements.chatMessages.innerHTML = welcomeHTML;
}

// ==================== API FUNCTIONS ====================
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
    } catch (error) {
    }
}

// ==================== MESSAGE HANDLING ====================
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function askQuestion(question) {
    elements.userInput.value = question;
    sendMessage();
}

async function sendMessage() {
    const question = elements.userInput.value.trim();
    if (!question) return;

    // Hide welcome
    const welcome = document.getElementById('welcome');
    if (welcome) {
        welcome.remove();
    }

    // Disable input
    elements.userInput.disabled = true;
    elements.sendButton.disabled = true;

    // Add user message
    addMessage('user', question);

    // Clear input
    elements.userInput.value = '';
    autoResize(elements.userInput);

    const startTime = Date.now();
    let currentAnswer = '';
    let metadata = {};
    let statusDiv = null;
    let answerDiv = null;

    // Show status indicator (minimalist - just dots)
    statusDiv = createStatusIndicator('...');
    elements.chatMessages.appendChild(statusDiv);
    scrollToBottom();

    // Add typing indicator
    const typingDiv = createTypingIndicator();
    elements.chatMessages.appendChild(typingDiv);
    scrollToBottom();

    try {
        // Create conversation ID if it doesn't exist
        if (!currentConversationId) {
            currentConversationId = 'conv_' + Date.now();
        }

        // Use regular /chat endpoint
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                chat_history: chatHistory,
                thread_id: currentConversationId
            })
        });

        const data = await response.json();

        // Remove status
        if (statusDiv) statusDiv.remove();
        if (typingDiv) typingDiv.remove();

        // Create answer message
        currentAnswer = data.answer;
        answerDiv = createAssistantMessage();
        updateMessageContent(answerDiv, currentAnswer);
        elements.chatMessages.appendChild(answerDiv);
        scrollToBottom();

        // Store metadata
        metadata = data.metadata || {};
        lastResponseTime = data.processing_time || 0;
        lastCacheHit = metadata.cache_hit || false;
        // updatePerfBadge(); // Disabled

        // Add metadata to answer (disabled)
        // if (answerDiv && Object.keys(metadata).length > 0) {
        //     addMetadataToMessage(answerDiv, metadata);
        // }

        // Update history
        chatHistory.push(
            { role: 'user', content: question },
            { role: 'assistant', content: currentAnswer }
        );

        // Save conversation to localStorage
        saveConversation();

    } catch (error) {
        // Clean up on error
        if (statusDiv) statusDiv.remove();
        if (typingDiv) typingDiv.remove();
        if (answerDiv) answerDiv.remove();
        addMessage('assistant', 'Désolé, une erreur est survenue. Veuillez réessayer.');
        console.error('Error:', error);
    } finally {
        // Re-enable input
        elements.userInput.disabled = false;
        elements.sendButton.disabled = false;
        elements.userInput.focus();
    }
}

// ==================== UI HELPER FUNCTIONS ====================
function addMessage(role, content, metadata = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const time = new Date().toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
    });

    const avatar = role === 'user' ? '<div class="user-avatar">U</div>' : '<img src="givaudan-logo.png" class="logo-avatar" alt="Givaudan">';
    const roleName = role === 'user' ? 'Vous' : 'Assistant';

    let metadataHTML = '';
    if (metadata && Object.keys(metadata).length > 0) {
        metadataHTML = createMetadataHTML(metadata);
    }

    const formattedContent = role === 'assistant' ? formatMarkdown(content) : escapeHtml(content);

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-role">${roleName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-text">${formattedContent}</div>
            ${metadataHTML}
        </div>
    `;

    elements.chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function createAssistantMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';

    const time = new Date().toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
    });

    messageDiv.innerHTML = `
        <div class="message-avatar"><img src="givaudan-logo.png" class="logo-avatar" alt="Givaudan"></div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-role">Assistant</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-text"></div>
        </div>
    `;

    return messageDiv;
}

function updateMessageContent(messageDiv, content) {
    const textDiv = messageDiv.querySelector('.message-text');
    if (textDiv) {
        textDiv.innerHTML = formatMarkdown(content);
    }
}

// Simple Markdown formatter
function formatMarkdown(text) {
    if (!text) return '';

    // Escape HTML first
    let html = escapeHtml(text);

    // Bold: **text** or __text__
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Code blocks: ```code```
    html = html.replace(/```(.+?)```/gs, '<pre><code>$1</code></pre>');

    // Inline code: `code`
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Split by double newlines to process paragraphs and lists separately
    const sections = html.split(/\n\n+/);
    const processed = sections.map(section => {
        // Check if it's a numbered list
        if (/^\d+\.\s+/.test(section)) {
            const items = section.split('\n')
                .filter(line => line.trim())
                .map(line => line.replace(/^\d+\.\s+/, '<li>') + '</li>')
                .join('');
            return '<ol>' + items + '</ol>';
        }
        // Check if it's a bullet list
        else if (/^[-*]\s+/.test(section)) {
            const items = section.split('\n')
                .filter(line => line.trim())
                .map(line => line.replace(/^[-*]\s+/, '<li>') + '</li>')
                .join('');
            return '<ul>' + items + '</ul>';
        }
        // Regular paragraph
        else {
            return '<p>' + section.replace(/\n/g, '<br>') + '</p>';
        }
    });

    html = processed.join('');

    // Italic: *text* or _text_ (after lists to avoid conflict)
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.+?)_/g, '<em>$1</em>');

    return html;
}

function addMetadataToMessage(messageDiv, metadata) {
    const metadataHTML = createMetadataHTML(metadata);
    const contentDiv = messageDiv.querySelector('.message-content');
    if (contentDiv) {
        contentDiv.innerHTML += metadataHTML;
    }
}

function createMetadataHTML(metadata) {
    const items = [];

    if (metadata.cache_hit) {
        items.push('<span class="metadata-item">Cache hit!</span>');
    }

    if (metadata.processing_time) {
        const time = metadata.processing_time;
        items.push(`<span class="metadata-item">${time.toFixed(2)}s</span>`);
    }

    if (metadata.num_actions !== undefined) {
        items.push(`<span class="metadata-item">${metadata.num_actions} action${metadata.num_actions > 1 ? 's' : ''}</span>`);
    }

    if (metadata.tools_used && metadata.tools_used.length > 0) {
        const toolNames = metadata.tools_used.map(t =>
            t.replace('search_vector_database', 'VectorDB')
             .replace('search_web', 'Web')
        ).join(', ');
        items.push(`<span class="metadata-item">${toolNames}</span>`);
    }

    if (items.length > 0) {
        return `<div class="message-metadata">${items.join('')}</div>`;
    }

    return '';
}

function createStatusIndicator(message) {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'status-indicator active';
    statusDiv.innerHTML = `<span class="simple-loading">${message}</span>`;
    return statusDiv;
}

function createTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator active';
    typingDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    return typingDiv;
}

function updatePerfBadge() {
    if (lastResponseTime !== null) {
        const cacheIndicator = lastCacheHit
            ? '<span class="badge cached">Cached</span>'
            : '<span class="badge">Search</span>';

        const speedIndicator = lastResponseTime < 2
            ? '<span class="badge fast">Ultra-fast</span>'
            : lastResponseTime < 10
            ? '<span class="badge fast">Fast</span>'
            : '<span class="badge">' + lastResponseTime.toFixed(1) + 's</span>';

        elements.perfBadge.innerHTML = cacheIndicator + speedIndicator;
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function scrollToBottom() {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== START ====================
window.addEventListener('load', init);
