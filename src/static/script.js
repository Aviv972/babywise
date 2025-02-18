document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const submitButton = chatForm.querySelector('button');
    
    let awaitingAnswer = false;
    let currentField = null;
    let sessionId = 'default';  // Add session ID

    // Function to detect text direction
    function isRTL(text) {
        const rtlChars = /[\u0591-\u07FF\u200F\u202B\u202E\uFB1D-\uFDFD\uFE70-\uFEFC]/;
        return rtlChars.test(text);
    }

    function addMessage(data, type) {
        console.log("Adding message:", { data, type });
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        if (typeof data === 'string') {
            messageDiv.textContent = data;
        }
        else if (data && (data.type === 'answer' || data.type === 'question')) {
            // Create structured message
            const content = document.createElement('div');
            content.className = 'message-content';
            
            // Add main text
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.textContent = data.text;
            content.appendChild(textDiv);
            
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
                    content.appendChild(productsDiv);
                }
            }
            
            messageDiv.appendChild(content);
        }
        else if (data && data.text) {
            messageDiv.textContent = data.text;
        }
        else {
            console.error("Unknown message format:", data);
            messageDiv.textContent = "Unknown message format";
        }
        
        // Auto-detect direction
        if (isRTL(messageDiv.textContent)) {
            messageDiv.style.direction = 'rtl';
            messageDiv.style.textAlign = 'right';
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Auto-detect input direction
    messageInput.addEventListener('input', function() {
        const isRtl = isRTL(this.value);
        this.style.direction = isRtl ? 'rtl' : 'ltr';
        this.style.textAlign = isRtl ? 'right' : 'left';
    });

    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;

        // Disable input and button while processing
        messageInput.disabled = true;
        submitButton.disabled = true;

        // Add user message to chat
        addMessage({ type: "user", text: message }, 'user');
        messageInput.value = '';

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

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Raw response from server:", data);

            // Handle different response types
            if (data && data.type) {
                console.log(`Processing ${data.type} response:`, data);
                addMessage(data, data.type === "question" ? 'bot-question' : 'bot');
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
            console.error('Error:', error);
            addMessage({
                type: "answer",
                text: 'Sorry, I encountered an error. Please try again.',
                metadata: { category: "error" }
            }, 'system');
        } finally {
            // Re-enable input and button
            messageInput.disabled = false;
            submitButton.disabled = false;
            messageInput.focus();
        }
    });
}); 