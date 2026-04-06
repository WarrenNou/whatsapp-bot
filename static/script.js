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
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });

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

        this.addMessage(message, 'user');

        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';

        this.showTyping();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, session_id: this.sessionId })
            });

            if (!response.ok) {
                throw new Error('HTTP error! status: ' + response.status);
            }

            const data = await response.json();
            this.hideTyping();

            if (data.message) {
                this.addMessage(data.message, 'bot');
            } else {
                this.addMessage('I apologize, but I encountered an error. Please try again.', 'bot');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTyping();
            this.addMessage("I'm having trouble connecting. Please check your internet connection and try again.", 'bot');
        }
    }

    sendQuickMessage(message) {
        this.messageInput.value = message;
        this.sendMessage();
    }

    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + sender + '-message';

        const currentTime = this.formatTime(new Date());
        const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

        const copyButton = sender === 'bot' ? '<button class="copy-button" onclick="copyMessage(\'' + messageId + '\')" title="Copy message" aria-label="Copy message"><i class="fas fa-copy"></i></button>' : '';

        messageDiv.innerHTML =
            '<div class="message-avatar" aria-hidden="true">' +
                '<i class="fas ' + (sender === 'user' ? 'fa-user' : 'fa-robot') + '"></i>' +
            '</div>' +
            '<div class="message-content">' +
                '<div class="message-text" id="' + messageId + '">' + this.formatMessage(text) + '</div>' +
                '<div class="message-footer">' +
                    '<div class="message-time">' + currentTime + '</div>' +
                    copyButton +
                '</div>' +
            '</div>';

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(text) {
        // Format URLs first (before converting line breaks)
        var formatted = text.replace(/(https?:\/\/[^\s\n<>]+?)(?=\s|$|\n|<)/g, function(match, url) {
            return '<a href="' + url + '" target="_blank" rel="noopener noreferrer" style="color: var(--accent-secondary); text-decoration: underline; text-underline-offset: 2px;">' + url + '</a>';
        });

        // Convert line breaks
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
        setTimeout(function() {
            var el = document.getElementById('chat-messages');
            if (el) el.scrollTop = el.scrollHeight;
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
    var messageElement = document.getElementById(messageId);
    if (!messageElement) return;

    var textToCopy = messageElement.innerText || messageElement.textContent;

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(function() {
            showCopyNotification();
        }).catch(function() {
            fallbackCopyTextToClipboard(textToCopy);
        });
    } else {
        fallbackCopyTextToClipboard(textToCopy);
    }
}

// Fallback copy function for older browsers
function fallbackCopyTextToClipboard(text) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        var successful = document.execCommand('copy');
        if (successful) showCopyNotification();
    } catch (err) {
        console.error('Fallback: unable to copy', err);
    }

    document.body.removeChild(textArea);
}

// Show copy notification
function showCopyNotification() {
    var existing = document.querySelector('.copy-notification');
    if (existing) existing.remove();

    var notification = document.createElement('div');
    notification.className = 'copy-notification';
    notification.innerHTML = '<i class="fas fa-check"></i> Copied to clipboard';

    document.body.appendChild(notification);

    requestAnimationFrame(function() {
        requestAnimationFrame(function() {
            notification.classList.add('show');
        });
    });

    setTimeout(function() {
        notification.classList.remove('show');
        setTimeout(function() {
            if (notification.parentNode) notification.parentNode.removeChild(notification);
        }, 300);
    }, 2000);
}

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.chatBot = new ChatBot();
    loadMarketTicker();
    setInterval(loadMarketTicker, 300000);
});

// Market ticker loader
async function loadMarketTicker() {
    var tickerContent = document.getElementById('ticker-content');
    if (!tickerContent) return;

    try {
        var resp = await fetch('/api/crypto');
        if (!resp.ok) throw new Error('fetch failed');
        var data = await resp.json();
        var coins = (data.data && data.data.coins) || {};

        var names = {
            bitcoin: 'BTC', ethereum: 'ETH', tether: 'USDT',
            binancecoin: 'BNB', solana: 'SOL', ripple: 'XRP',
            cardano: 'ADA', dogecoin: 'DOGE'
        };

        var items = [];
        for (var id in coins) {
            if (!coins.hasOwnProperty(id)) continue;
            var info = coins[id];
            var ticker = names[id] || id.toUpperCase();
            var price = info.price_usd >= 1
                ? '$' + info.price_usd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})
                : '$' + info.price_usd.toLocaleString(undefined, {minimumFractionDigits: 4, maximumFractionDigits: 4});
            var change = info.change_24h_pct;
            var cls = change >= 0 ? 'ticker-up' : 'ticker-down';
            var sign = change >= 0 ? '+' : '';
            items.push(
                '<span class="ticker-item"><span class="ticker-label">' + ticker + '</span> <span class="ticker-price">' + price + '</span> <span class="' + cls + '">' + sign + change.toFixed(2) + '%</span></span>'
            );
        }

        if (items.length > 0) {
            tickerContent.innerHTML = items.join('') + items.join('');
        }
    } catch (e) {
        console.debug('Ticker update skipped:', e.message);
    }
}

// Entrance animations & interactions
document.addEventListener('DOMContentLoaded', function() {
    // Animate welcome message on load
    var messages = document.querySelectorAll('.message');
    messages.forEach(function(message, index) {
        message.style.opacity = '0';
        message.style.transform = 'translateY(12px)';
        setTimeout(function() {
            message.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            message.style.opacity = '1';
            message.style.transform = 'translateY(0)';
        }, index * 80 + 150);
    });

    // Ripple effect on buttons
    var buttons = document.querySelectorAll('.quick-btn, #send-button');
    buttons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var ripple = document.createElement('div');
            var rect = this.getBoundingClientRect();
            var size = Math.max(rect.width, rect.height);
            var x = e.clientX - rect.left - size / 2;
            var y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');

            this.appendChild(ripple);
            setTimeout(function() { ripple.remove(); }, 600);
        });
    });
});

// Injected styles for dynamic elements
(function() {
    var style = document.createElement('style');
    style.textContent =
        '.quick-btn, #send-button { position: relative; overflow: hidden; }' +

        '.ripple {' +
            'position: absolute; border-radius: 50%;' +
            'background: rgba(255, 255, 255, 0.25);' +
            'transform: scale(0);' +
            'animation: ripple-animation 0.6s linear;' +
            'pointer-events: none;' +
        '}' +

        '@keyframes ripple-animation {' +
            'to { transform: scale(4); opacity: 0; }' +
        '}' +

        '.message-footer {' +
            'display: flex; justify-content: space-between; align-items: center; margin-top: 4px;' +
        '}' +

        '.copy-button {' +
            'background: none; border: none; color: var(--text-muted); cursor: pointer;' +
            'padding: 4px 6px; border-radius: 4px; font-size: 0.78em;' +
            'transition: all 0.2s ease; opacity: 0;' +
        '}' +

        '.message:hover .copy-button { opacity: 0.7; }' +

        '.copy-button:hover {' +
            'color: var(--accent-secondary); background: rgba(99, 102, 241, 0.1); opacity: 1 !important;' +
        '}' +

        '.copy-notification {' +
            'position: fixed; top: 20px; right: 20px;' +
            'background: var(--bg-elevated); color: var(--green);' +
            'padding: 10px 18px; border-radius: var(--radius-md);' +
            'font-size: 0.85em; font-weight: 500;' +
            'box-shadow: var(--shadow-md); border: 1px solid var(--border-subtle);' +
            'transform: translateX(400px); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);' +
            'z-index: 1000; display: flex; align-items: center; gap: 8px;' +
        '}' +

        '.copy-notification.show { transform: translateX(0); }' +

        '.copy-notification i { font-size: 0.95em; }';

    document.head.appendChild(style);
})();
