document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const submitButton = chatForm.querySelector('button');
    const typingIndicator = document.getElementById('typing-indicator');
    const disclaimerOverlay = document.getElementById('disclaimerOverlay');
    const closeDisclaimerButton = document.getElementById('closeDisclaimer');
    
    let awaitingAnswer = false;
    let currentField = null;
    let sessionId = 'default';
    let lastMessageGroup = null;

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

    function addMessage(data, type) {
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
            contentDiv.textContent = data.text;
            
            // Add product grid if available
            if (data.products && data.products.length > 0) {
                const productsDiv = document.createElement('div');
                productsDiv.className = 'products-grid';
                
                data.products.forEach(product => {
                    if (product.name && !product.name.startsWith('-')) {
                        const productCard = document.createElement('div');
                        productCard.className = 'product-card';
                        productCard.innerHTML = `
                            <h3>${product.name}</h3>
                            ${product.price ? `<div class="price">${product.price}</div>` : ''}
                            ${product.features ? `<div class="features">${product.features}</div>` : ''}
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
        
        // Smooth scroll to bottom
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });
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
        // Hebrew detection
        const hebrewPattern = /[\u0590-\u05FF\u0600-\u06FF]/;
        if (hebrewPattern.test(text)) return 'he';
        
        // Add more language detection patterns as needed
        // Arabic
        const arabicPattern = /[\u0600-\u06FF]/;
        if (arabicPattern.test(text)) return 'ar';
        
        // Default to English
        return 'en';
    }

    // Handle form submission
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
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    session_id: sessionId,
                    language: detectedLanguage // Send detected language to backend
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

    // Add welcome message on load
    addWelcomeMessage();

    // Initial button state
    submitButton.disabled = true;
    submitButton.style.color = '#8696A0';

    // Hide typing indicator initially
    typingIndicator.style.display = 'none';

    // Handle disclaimer popup
    function handleDisclaimer() {
        // Check if user has seen the disclaimer in this session
        if (!sessionStorage.getItem('disclaimerAccepted')) {
            disclaimerOverlay.style.display = 'flex';
        } else {
            disclaimerOverlay.style.display = 'none';
        }
    }

    // Close disclaimer and store in session
    closeDisclaimerButton.addEventListener('click', function() {
        disclaimerOverlay.style.display = 'none';
        sessionStorage.setItem('disclaimerAccepted', 'true');
    });

    // Show disclaimer on page load
    handleDisclaimer();
}); 