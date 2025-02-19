document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const submitButton = chatForm.querySelector('button');
    const typingIndicator = document.getElementById('typing-indicator');
    
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
        const welcomeText = `👋 Hi there! I'm your friendly Babywise Assistant, here to help make your parenting journey a little easier. I can help you with: 😊 Parenting Guidance - Sleep schedules and routines - Feeding advice and meal planning - Development milestones - Daily care and routines - Behavior and learning tips\n\n🛍️ Baby Gear Support - Product recommendations when needed - Personalized suggestions for your needs - Help finding the right gear for your family How can I assist you today? Feel free to ask about any parenting topics or baby gear questions!`;

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
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
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
            // Add main text
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.textContent = data.text;
            contentDiv.appendChild(textDiv);
            
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
                messageDiv.style.marginTop = '12px';
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
        
        // Insert message in correct order
        if (typingIndicator && type === 'user') {
            chatMessages.insertBefore(messageDiv, typingIndicator);
        } else {
            chatMessages.appendChild(messageDiv);
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
        submitButton.style.color = this.value.trim() ? 'var(--whatsapp-green)' : '#8696A0';
    });

    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;

        // Disable input while processing
        messageInput.disabled = true;
        submitButton.disabled = true;

        // Add user message to chat
        addMessage({ type: "user", text: message }, 'user');
        messageInput.value = '';

        // Show typing indicator with delay
        setTimeout(() => {
            typingIndicator.style.display = 'block';
            chatMessages.scrollTo({
                top: chatMessages.scrollHeight,
                behavior: 'smooth'
            });
        }, 200);

        try {
            console.log("Sending request to /chat with:", { message, sessionId });
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    session_id: sessionId
                }),
            });

            // Hide typing indicator with delay
            setTimeout(() => {
                typingIndicator.style.display = 'none';
            }, 500);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Raw response from server:", data);

            // Handle different response types
            if (data && data.type) {
                console.log(`Processing ${data.type} response:`, data);
                // Add slight delay to simulate typing
                setTimeout(() => {
                    addMessage(data, data.type === "question" ? 'assistant' : 'assistant');
                }, 700);
            } else {
                console.error("Unexpected response format:", data);
                console.error("Response structure:", JSON.stringify(data, null, 2));
                addMessage({
                    type: "answer",
                    text: "I apologize, but I received an unexpected response format. Please try again.",
                    metadata: { category: "error" }
                }, 'system');
            }

        } catch (error) {
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            console.error('Error:', error);
            addMessage({
                type: "answer",
                text: 'Sorry, I encountered an error. Please try again.',
                metadata: { category: "error" }
            }, 'system');
        } finally {
            // Re-enable input and button
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
}); 