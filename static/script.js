class ChatBot {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.isTyping = false;
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.typingIndicator = document.getElementById('typing-indicator');
        
        this.initializeEventListeners();
        this.updateWelcomeTime();
    }
    
    generateSessionId() {
        return 'web_session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeEventListeners() {
        // Enter key to send message
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize input
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });
        
        // Focus input on load
        this.messageInput.focus();
    }
    
    updateWelcomeTime() {
        const welcomeMessage = document.querySelector('.welcome-message .message-time');
        if (welcomeMessage) {
            welcomeMessage.textContent = this.formatTime(new Date());
        }
    }
    
    formatTime(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide typing indicator
            this.hideTyping();
            
            // Add bot response
            if (data.message) {
                this.addMessage(data.message, 'bot');
            } else {
                this.addMessage('I apologize, but I encountered an error. Please try again.', 'bot');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTyping();
            this.addMessage('I\'m having trouble connecting. Please check your internet connection and try again.', 'bot');
        }
    }
    
    sendQuickMessage(message) {
        this.messageInput.value = message;
        this.sendMessage();
    }
    
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const currentTime = this.formatTime(new Date());
        const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Add copy button only for bot messages
        const copyButton = sender === 'bot' ? `
            <button class="copy-button" onclick="copyMessage('${messageId}')" title="Copy message">
                <i class="fas fa-copy"></i>
            </button>
        ` : '';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas ${sender === 'user' ? 'fa-user' : 'fa-robot'}"></i>
            </div>
            <div class="message-content">
                <div class="message-text" id="${messageId}">${this.formatMessage(text)}</div>
                <div class="message-footer">
                    <div class="message-time">${currentTime}</div>
                    ${copyButton}
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(text) {
        // Sanitize a URL: only allow http/https schemes to prevent XSS via javascript: etc.
        const sanitizeUrl = (url) => {
            try {
                const parsed = new URL(url);
                if (parsed.protocol.toLowerCase() === 'http:' || parsed.protocol.toLowerCase() === 'https:') {
                    return url;
                }
            } catch (_) { /* invalid URL */ }
            return '#';
        };

        // Format URLs (before converting line breaks)
        let formatted = text.replace(/(https?:\/\/[^\s\n<>]+?)(?=\s|$|\n|<)/g, (match, url) => {
            const safeUrl = sanitizeUrl(url);
            return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-blue);text-decoration:underline;">${url}</a>`;
        });

        // Convert line breaks to HTML
        formatted = formatted.replace(/\n/g, '<br>');

        // Format bold text (markdown-style)
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        return formatted;
    }
    
    showTyping() {
        this.isTyping = true;
        this.typingIndicator.classList.add('show');
        this.sendButton.disabled = true;
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('show');
        this.sendButton.disabled = false;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
}

// Global functions for quick buttons
function sendQuickMessage(message) {
    if (window.chatBot) {
        window.chatBot.sendQuickMessage(message);
    }
}

function sendMessage() {
    if (window.chatBot) {
        window.chatBot.sendMessage();
    }
}

// Copy message function
function copyMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    if (!messageElement) return;
    
    // Get the text content without HTML tags
    const textToCopy = messageElement.innerText || messageElement.textContent;
    
    // Use the modern clipboard API if available
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(() => {
            showCopyNotification();
        }).catch(err => {
            console.error('Failed to copy: ', err);
            fallbackCopyTextToClipboard(textToCopy);
        });
    } else {
        // Fallback for older browsers
        fallbackCopyTextToClipboard(textToCopy);
    }
}

// Fallback copy function for older browsers
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    
    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopyNotification();
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
    }
    
    document.body.removeChild(textArea);
}

// Show copy notification
function showCopyNotification() {
    // Remove any existing notification
    const existing = document.querySelector('.copy-notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = 'copy-notification';
    notification.innerHTML = '<i class="fas fa-check"></i> Copied to clipboard';
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Hide and remove notification
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 2000);
}

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatBot = new ChatBot();
    // Load market ticker data
    loadMarketTicker();
    // Refresh ticker every 5 minutes
    setInterval(loadMarketTicker, 300000);
});

// Market ticker loader
async function loadMarketTicker() {
    const tickerContent = document.getElementById('ticker-content');
    if (!tickerContent) return;

    try {
        const resp = await fetch('/api/crypto');
        if (!resp.ok) throw new Error('fetch failed');
        const data = await resp.json();
        const coins = (data.data && data.data.coins) || {};

        const names = {
            bitcoin: 'BTC', ethereum: 'ETH', tether: 'USDT',
            binancecoin: 'BNB', solana: 'SOL', ripple: 'XRP',
            cardano: 'ADA', dogecoin: 'DOGE'
        };

        let items = [];
        for (const [id, info] of Object.entries(coins)) {
            const ticker = names[id] || id.toUpperCase();
            const price = info.price_usd >= 1
                ? '$' + info.price_usd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})
                : '$' + info.price_usd.toLocaleString(undefined, {minimumFractionDigits: 4, maximumFractionDigits: 4});
            const change = info.change_24h_pct;
            const cls = change >= 0 ? 'ticker-up' : 'ticker-down';
            const sign = change >= 0 ? '+' : '';
            items.push(
                `<span class="ticker-item"><span class="ticker-label">${ticker}</span> <span class="ticker-price">${price}</span> <span class="${cls}">${sign}${change.toFixed(2)}%</span></span>`
            );
        }

        if (items.length > 0) {
            // Duplicate for seamless infinite scroll
            const html = items.join('') + items.join('');
            tickerContent.innerHTML = html;
        }
    } catch (e) {
        // Silently keep the loading text or previous data
        console.debug('Ticker update skipped:', e.message);
    }
}

// Add some nice effects
document.addEventListener('DOMContentLoaded', () => {
    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('.quick-btn, #send-button');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('div');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');

            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
});

// Add CSS for ripple effect and copy functionality
const style = document.createElement('style');
style.textContent = `
    .quick-btn, #send-button {
        position: relative;
        overflow: hidden;
    }

    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.25);
        transform: scale(0);
        animation: ripple-animation 0.55s linear;
        pointer-events: none;
    }

    @keyframes ripple-animation {
        to { transform: scale(4); opacity: 0; }
    }

    /* Copy button */
    .message-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 6px;
    }

    .copy-button {
        background: none;
        border: none;
        color: var(--text-muted, #4a5568);
        cursor: pointer;
        padding: 4px 6px;
        border-radius: 6px;
        font-size: 0.75em;
        transition: all 0.18s ease;
        opacity: 0.7;
    }

    .copy-button:hover {
        color: var(--accent-blue, #4f8cff);
        background: rgba(79,140,255,0.12);
        opacity: 1;
    }

    /* Copy notification */
    .copy-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #1a2035, #141929);
        border: 1px solid rgba(79,140,255,0.3);
        color: #e8eaf2;
        padding: 10px 18px;
        border-radius: 10px;
        font-size: 0.85em;
        font-weight: 500;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        transform: translateX(400px);
        transition: transform 0.28s cubic-bezier(0.22,1,0.36,1);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .copy-notification.show {
        transform: translateX(0);
    }

    .copy-notification i {
        color: #48bb78;
    }
`;
document.head.appendChild(style);
