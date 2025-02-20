document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const submitButton = chatForm.querySelector('button');
    const typingIndicator = document.getElementById('typing-indicator');
    const disclaimerOverlay = document.getElementById('disclaimerOverlay');
    const closeDisclaimerButton = document.getElementById('closeDisclaimer');
    const newChatButton = document.getElementById('newChatButton');
    
    let awaitingAnswer = false;
    let currentField = null;
    let lastMessageGroup = null;

    // Initialize or get existing session ID
    let sessionId = localStorage.getItem('sessionId');
    if (!sessionId) {
        sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('sessionId', sessionId);
    }

    // Clear any existing disclaimer acceptance on page load
    if (window.location.href.includes('?new')) {
        sessionStorage.removeItem('disclaimerAccepted');
        sessionStorage.removeItem('disclaimerShown');
    }

    // Load chat history from localStorage
    function loadChatHistory() {
        const currentChat = localStorage.getItem(`chat_${sessionId}`);
        if (currentChat) {
            try {
                const messages = JSON.parse(currentChat);
                chatMessages.innerHTML = ''; // Clear existing messages
                messages.forEach(msg => {
                    addMessage(msg.data, msg.type, false); // false means don't save to localStorage
                });
                scrollToBottom();
            } catch (e) {
                console.error('Error loading chat history:', e);
            }
        } else {
            addWelcomeMessage();
        }
    }

    // Save message to chat history
    function saveMessageToHistory(data, type) {
        try {
            let currentChat = localStorage.getItem(`chat_${sessionId}`);
            let messages = currentChat ? JSON.parse(currentChat) : [];
            messages.push({ data, type, timestamp: new Date().toISOString() });
            localStorage.setItem(`chat_${sessionId}`, JSON.stringify(messages));
        } catch (e) {
            console.error('Error saving message to history:', e);
        }
    }

    // Start new chat session
    function startNewChat() {
        // Remove old session data
        localStorage.removeItem(`chat_${sessionId}`);
        
        // Generate new session ID
        sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('sessionId', sessionId);
        
        // Clear messages
        chatMessages.innerHTML = '';
        
        // Add welcome message
        addWelcomeMessage();
        
        // Save initial state
        saveMessageToHistory({
            type: 'welcome',
            text: chatMessages.querySelector('.message').textContent
        }, 'assistant');
    }

    // Scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });
    }

    // Function to detect text direction
    function isRTL(text) {
        const rtlChars = /[\u0591-\u07FF\u200F\u202B\u202E\uFB1D-\uFDFD\uFE70-\uFEFC]/;
        return rtlChars.test(text);
    }

    // Add welcome message
    function addWelcomeMessage() {
        const welcomeText = `👋 Hi there! I'm your friendly Babywise Assistant, here to help make your parenting journey a little easier. I can help you with: 😊 Parenting Guidance - Sleep schedules and routines - Feeding advice and meal planning - Development milestones - Daily care and routines - Behavior and learning tips

🛍️ Baby Gear Support - Product recommendations when needed - Personalized suggestions for your needs - Help finding the right gear for your family How can I assist you today? Feel free to ask about any parenting topics or baby gear questions!`;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = welcomeText;
        
        messageDiv.appendChild(contentDiv);
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = formatTimestamp(new Date());
        messageDiv.appendChild(timestamp);
        
        // Insert welcome message at the beginning
        chatMessages.insertBefore(messageDiv, chatMessages.firstChild);
        
        // Move typing indicator to be after the welcome message
        if (typingIndicator) {
            chatMessages.appendChild(typingIndicator);
        }
    }

    function formatTimestamp(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }

    function shouldGroupMessage(type, lastGroup) {
        if (!lastGroup) return false;
        if (lastGroup.type !== type) return false;
        
        const lastTime = new Date(lastGroup.timestamp);
        const currentTime = new Date();
        const timeDiff = (currentTime - lastTime) / 1000; // difference in seconds
        
        return timeDiff < 60; // group messages if less than 1 minute apart
    }

    // Modified addMessage function to include history saving
    function addMessage(data, type, saveToHistory = true) {
        try {
            console.log("Adding message:", { data, type });
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            // Create message content container
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            // Handle different message formats
            if (typeof data === 'string') {
                contentDiv.textContent = data;
            }
            else if (data && (data.type === 'answer' || data.type === 'question')) {
                contentDiv.textContent = data.text || 'No message content';
                
                // Add product grid if available
                if (data.products && Array.isArray(data.products) && data.products.length > 0) {
                    const productsDiv = document.createElement('div');
                    productsDiv.className = 'products-grid';
                    
                    data.products.forEach(product => {
                        if (product && product.name && !product.name.startsWith('-')) {
                            const productCard = document.createElement('div');
                            productCard.className = 'product-card';
                            productCard.innerHTML = `
                                <h3>${product.name}</h3>
                                ${product.price ? `<div class="price">${product.price}</div>` : ''}
                            `;
                            productsDiv.appendChild(productCard);
                        }
                    });
                    
                    if (productsDiv.children.length > 0) {
                        contentDiv.appendChild(productsDiv);
                    }
                }
            }
            else if (data && data.text) {
                contentDiv.textContent = data.text;
            }
            else {
                console.error("Unknown message format:", data);
                contentDiv.textContent = "Unknown message format";
            }
            
            messageDiv.appendChild(contentDiv);
            
            // Handle message grouping
            const shouldGroup = shouldGroupMessage(type, lastMessageGroup);
            if (!shouldGroup) {
                // Add timestamp only for first message in group
                const timestamp = document.createElement('div');
                timestamp.className = 'message-timestamp';
                timestamp.textContent = formatTimestamp(new Date());
                messageDiv.appendChild(timestamp);
                
                // Update spacing classes
                if (lastMessageGroup && lastMessageGroup.type !== type) {
                    messageDiv.style.marginTop = '8px';
                }
            } else {
                messageDiv.style.marginTop = '1px';
            }
            
            // Update last message group
            lastMessageGroup = {
                type: type,
                timestamp: new Date()
            };
            
            // Auto-detect direction
            if (isRTL(messageDiv.textContent)) {
                messageDiv.style.direction = 'rtl';
                messageDiv.style.textAlign = 'right';
            }
            
            // Always append new messages at the end
            chatMessages.appendChild(messageDiv);
            
            // Move typing indicator to be last
            if (typingIndicator) {
                chatMessages.appendChild(typingIndicator);
            }
            
            // Save to history if needed
            if (saveToHistory) {
                saveMessageToHistory(data, type);
            }
            
            scrollToBottom();
        } catch (error) {
            console.error('Error adding message:', error);
        }
    }

    // Handle input changes
    messageInput.addEventListener('input', function() {
        // Auto-detect direction
        const isRtl = isRTL(this.value);
        this.style.direction = isRtl ? 'rtl' : 'ltr';
        this.style.textAlign = isRtl ? 'right' : 'left';
        
        // Toggle send button state
        submitButton.disabled = !this.value.trim();
        submitButton.style.color = this.value.trim() ? '#00a884' : '#8696a0';
    });

    // Language detection function
    function detectLanguage(text) {
        // Hebrew detection (excluding Arabic range)
        const hebrewPattern = /[\u0590-\u05FF]/;
        if (hebrewPattern.test(text)) return 'he';
        
        // Arabic detection
        const arabicPattern = /[\u0600-\u06FF]/;
        if (arabicPattern.test(text)) return 'ar';
        
        // Default to English
        return 'en';
    }

    // Handle new chat button click
    newChatButton.addEventListener('click', function() {
        // Show confirmation dialog
        const confirmNewChat = confirm('Start a new chat? Your current conversation will be saved in history.');
        
        if (confirmNewChat) {
            // Add visual feedback
            newChatButton.style.transform = 'scale(0.95)';
            setTimeout(() => {
                newChatButton.style.transform = 'scale(1)';
            }, 200);
            
            // Start new chat
            startNewChat();
            
            // Show feedback message
            addMessage({
                type: 'system',
                text: 'Started a new chat session. Previous chat has been saved.'
            }, 'system');
        }
    });

    // Modified form submission to include session ID
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;

        // Detect message language
        const detectedLanguage = detectLanguage(message);

        // Disable input while processing
        messageInput.disabled = true;
        submitButton.disabled = true;

        // Add user message to chat
        addMessage({ type: "user", text: message }, 'user');
        messageInput.value = '';

        // Show typing indicator
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    session_id: sessionId,
                    language: detectedLanguage
                }),
            });

            typingIndicator.style.display = 'none';

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Raw response from server:", data);

            if (data && data.type) {
                setTimeout(() => {
                    addMessage(data, data.type === "question" ? 'assistant' : 'assistant');
                }, 700);
            } else {
                console.error("Unexpected response format:", data);
                addMessage({
                    type: "answer",
                    text: detectedLanguage === 'he' 
                        ? 'מצטער, אך התקבלה תשובה בפורמט לא צפוי. אנא נסה שוב.'
                        : 'I apologize, but I received an unexpected response format. Please try again.',
                    metadata: { category: "error" }
                }, 'system');
            }

        } catch (error) {
            typingIndicator.style.display = 'none';
            
            console.error('Error:', error);
            addMessage({
                type: "answer",
                text: detectedLanguage === 'he'
                    ? 'מצטער, אך אירעה שגיאה. אנא נסה שוב.'
                    : 'Sorry, I encountered an error. Please try again.',
                metadata: { category: "error" }
            }, 'system');
        } finally {
            messageInput.disabled = false;
            submitButton.disabled = !messageInput.value.trim();
            messageInput.focus();
        }
    });

    // Load chat history on startup
    loadChatHistory();

    // Initial button state
    submitButton.disabled = true;
    submitButton.style.color = '#8696A0';

    // Hide typing indicator initially
    typingIndicator.style.display = 'none';

    // Show disclaimer if not already accepted
    if (!sessionStorage.getItem('disclaimerAccepted')) {
        disclaimerOverlay.style.display = 'flex';
    } else {
        disclaimerOverlay.style.display = 'none';
    }

    // Handle disclaimer close button
    closeDisclaimerButton.addEventListener('click', function() {
        sessionStorage.setItem('disclaimerAccepted', 'true');
        disclaimerOverlay.style.display = 'none';
    });
}); 