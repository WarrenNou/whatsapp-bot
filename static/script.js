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
        console.log('Original text:', text);
        
        // Format URLs first (before converting line breaks) - be very specific about URL endings
        let formatted = text.replace(/(https?:\/\/[^\s\n<>]+?)(?=\s|$|\n|<)/g, (match, url) => {
            console.log('Found URL:', url);
            return `<a href="${url}" target="_blank" style="color: #667eea; text-decoration: underline;">${url}</a>`;
        });
        
        console.log('After URL formatting:', formatted);
        
        // Convert line breaks to HTML
        formatted = formatted.replace(/\n/g, '<br>');
        
        console.log('After line break conversion:', formatted);
        
        // Format bold text (markdown-style)
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        console.log('Final formatted text:', formatted);
        
        // Format currency symbols and emojis (keep as is)
        // They're already in the text
        
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
});

// Add some nice effects
document.addEventListener('DOMContentLoaded', () => {
    // Animate messages on load
    const messages = document.querySelectorAll('.message');
    messages.forEach((message, index) => {
        message.style.opacity = '0';
        message.style.transform = 'translateY(20px)';
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s, transform 0.5s';
            message.style.opacity = '1';
            message.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
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
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    /* Copy button styles */
    .message-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 5px;
    }
    
    .copy-button {
        background: none;
        border: none;
        color: #9ca3af;
        cursor: pointer;
        padding: 5px;
        border-radius: 4px;
        font-size: 0.8em;
        transition: all 0.2s ease;
        opacity: 0.7;
    }
    
    .copy-button:hover {
        color: #667eea;
        background: rgba(102, 126, 234, 0.1);
        opacity: 1;
    }
    
    .bot-message .copy-button {
        color: #64748b;
    }
    
    .bot-message .copy-button:hover {
        color: #667eea;
        background: rgba(102, 126, 234, 0.1);
    }
    
    /* Copy notification styles */
    .copy-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 0.9em;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transform: translateX(400px);
        transition: transform 0.3s ease;
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .copy-notification.show {
        transform: translateX(0);
    }
    
    .copy-notification i {
        font-size: 1em;
    }
`;
document.head.appendChild(style);
