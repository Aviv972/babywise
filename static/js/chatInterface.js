/**
 * Babywise Assistant - Chat Interface
 * 
 * This script handles the chat interface functionality, including:
 * - Message submission and display
 * - API communication
 * - Session management
 * - Command parsing for routine tracking
 */

// Configuration
const CONFIG = {
    apiUrl: 'http://localhost:8080',
    debugMode: false,
    defaultLanguage: 'en'
};

// DOM Elements
const elements = {
    messagesContainer: document.getElementById('messagesContainer'),
    messageInput: document.getElementById('messageInput'),
    sendButton: document.getElementById('sendButton'),
    typingIndicator: document.getElementById('typingIndicator'),
    newChatBtn: document.getElementById('newChatBtn')
};

// State
let state = {
    threadId: localStorage.getItem('babywiseThreadId') || generateThreadId(),
    language: localStorage.getItem('babywiseLanguage') || CONFIG.defaultLanguage,
    messages: JSON.parse(localStorage.getItem('babywiseMessages') || '[]'),
    isWaitingForResponse: false
};

// Initialize the chat interface
function initChat() {
    // Save thread ID to localStorage
    localStorage.setItem('babywiseThreadId', state.threadId);
    
    // Load existing messages
    if (state.messages.length > 0) {
        state.messages.forEach(message => {
            addMessageToUI(message.content, message.type, message.timestamp);
        });
    } else {
        // Add welcome message if no messages exist
        const welcomeMessage = state.language === 'he' 
            ? 'שלום! אני העוזר של Babywise. כיצד אוכל לעזור לך היום עם הטיפול בתינוק שלך?'
            : 'Hello! I\'m the Babywise Assistant. How can I help you with your baby care today?';
        
        addBotMessage(welcomeMessage);
    }
    
    // Set up event listeners
    setupEventListeners();
}

// Set up event listeners
function setupEventListeners() {
    // Send message on button click
    elements.sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key (but allow Shift+Enter for new lines)
    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Enable/disable send button based on input content
    elements.messageInput.addEventListener('input', () => {
        elements.sendButton.disabled = elements.messageInput.value.trim() === '';
        
        // Auto-resize textarea
        elements.messageInput.style.height = 'auto';
        elements.messageInput.style.height = `${Math.min(elements.messageInput.scrollHeight, 120)}px`;
    });
    
    // New chat button
    elements.newChatBtn.addEventListener('click', () => {
        if (confirm('Start a new conversation? Your current chat history will be saved.')) {
            state.threadId = generateThreadId();
            localStorage.setItem('babywiseThreadId', state.threadId);
            state.messages = [];
            localStorage.setItem('babywiseMessages', JSON.stringify(state.messages));
            elements.messagesContainer.innerHTML = '';
            initChat();
        }
    });
}

// Send a message
async function sendMessage() {
    const messageText = elements.messageInput.value.trim();
    
    if (messageText === '' || state.isWaitingForResponse) {
        return;
    }
    
    // Add user message to UI
    addUserMessage(messageText);
    
    // Clear input
    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';
    elements.sendButton.disabled = true;
    
    // Check if message is a command
    const isCommand = parseCommand(messageText);
    
    if (!isCommand) {
        // If not a command, send to chatbot API
        await sendToChatAPI(messageText);
    }
}

// Add a user message to the UI and state
function addUserMessage(content) {
    const timestamp = new Date().toISOString();
    
    // Add to UI
    addMessageToUI(content, 'user', timestamp);
    
    // Add to state
    state.messages.push({
        content,
        type: 'user',
        timestamp
    });
    
    // Save to localStorage
    localStorage.setItem('babywiseMessages', JSON.stringify(state.messages));
}

// Add a bot message to the UI and state
function addBotMessage(content) {
    const timestamp = new Date().toISOString();
    
    // Add to UI
    addMessageToUI(content, 'bot', timestamp);
    
    // Add to state
    state.messages.push({
        content,
        type: 'bot',
        timestamp
    });
    
    // Save to localStorage
    localStorage.setItem('babywiseMessages', JSON.stringify(state.messages));
}

// Add a message to the UI
function addMessageToUI(content, type, timestamp) {
    const messageElement = document.createElement('div');
    messageElement.className = `message ${type === 'user' ? 'user-message' : 'bot-message'}`;
    
    // Check if the content should use RTL
    const isRTL = state.language === 'he' || /[\u0590-\u05FF]/.test(content);
    if (isRTL) {
        messageElement.classList.add('rtl');
    }
    
    // Format the timestamp
    const formattedTime = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Create message content
    messageElement.innerHTML = `
        <div class="message-content">${content}</div>
        <div class="timestamp">${formattedTime}</div>
    `;
    
    // Add to messages container
    elements.messagesContainer.appendChild(messageElement);
    
    // Scroll to bottom
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

// Send message to the chat API
async function sendToChatAPI(message) {
    try {
        // Show typing indicator
        showTypingIndicator();
        
        state.isWaitingForResponse = true;
        
        // Prepare request data
        const requestData = {
            message,
            thread_id: state.threadId,
            language: state.language
        };
        
        if (CONFIG.debugMode) {
            console.log('Sending to API:', requestData);
        }
        
        // In development, we'll simulate a response
        // In production, uncomment the fetch code below
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Simulate response
        const simulatedResponse = {
            response: "This is a simulated response from the Babywise Assistant. The actual API integration will be implemented in future phases.",
            context: { detected_domain: "general" },
            metadata: { timestamp: new Date().toISOString() }
        };
        
        // Process the response
        processResponse(simulatedResponse);
        
        /* 
        // Actual API call (uncomment in production)
        const response = await fetch(`${CONFIG.apiUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        processResponse(data);
        */
        
    } catch (error) {
        console.error('Error sending message:', error);
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Show error message
        addBotMessage('Sorry, I encountered an error. Please try again later.');
        
        state.isWaitingForResponse = false;
    }
}

// Process the API response
function processResponse(data) {
    if (CONFIG.debugMode) {
        console.log('API Response:', data);
    }
    
    // Hide typing indicator
    hideTypingIndicator();
    
    // Add bot message to UI
    addBotMessage(data.response);
    
    state.isWaitingForResponse = false;
}

// Parse command for routine tracking
function parseCommand(message) {
    // Simple command parsing for routine tracking
    const sleepPattern = /^(sleep|bed|nap)\s+(.+)$/i;
    const wakePattern = /^(woke|wake|awake)\s+(.+)$/i;
    const feedPattern = /^(feed|feeding|fed)\s+(.+)$/i;
    const donePattern = /^(done feeding|finished feeding)\s+(.+)$/i;
    const summaryPattern = /^summary\s+(today|week|month)$/i;
    const helpPattern = /^help\s+tracking$/i;
    
    let match;
    
    // Check for sleep start command
    if ((match = sleepPattern.exec(message)) !== null) {
        const time = match[2];
        handleSleepCommand('start', time);
        return true;
    }
    
    // Check for sleep end command
    if ((match = wakePattern.exec(message)) !== null) {
        const time = match[2];
        handleSleepCommand('end', time);
        return true;
    }
    
    // Check for feeding start command
    if ((match = feedPattern.exec(message)) !== null) {
        const time = match[2];
        handleFeedingCommand('start', time);
        return true;
    }
    
    // Check for feeding end command
    if ((match = donePattern.exec(message)) !== null) {
        const time = match[2];
        handleFeedingCommand('end', time);
        return true;
    }
    
    // Check for summary command
    if ((match = summaryPattern.exec(message)) !== null) {
        const period = match[1];
        handleSummaryCommand(period);
        return true;
    }
    
    // Check for help command
    if (helpPattern.test(message)) {
        showTrackingHelp();
        return true;
    }
    
    return false;
}

// Handle sleep command
function handleSleepCommand(action, timeStr) {
    // This is a placeholder for the actual implementation
    const response = action === 'start'
        ? `I've recorded that your baby went to sleep at ${timeStr}.`
        : `I've recorded that your baby woke up at ${timeStr}.`;
    
    // In the future, this will call the API to record the event
    setTimeout(() => {
        addBotMessage(response);
    }, 500);
}

// Handle feeding command
function handleFeedingCommand(action, timeStr) {
    // This is a placeholder for the actual implementation
    const response = action === 'start'
        ? `I've recorded that your baby started feeding at ${timeStr}.`
        : `I've recorded that your baby finished feeding at ${timeStr}.`;
    
    // In the future, this will call the API to record the event
    setTimeout(() => {
        addBotMessage(response);
    }, 500);
}

// Handle summary command
function handleSummaryCommand(period) {
    // This is a placeholder for the actual implementation
    const response = `Here's a summary of your baby's routine for the ${period}:\n\n` +
        `This feature will be implemented in future phases.`;
    
    // In the future, this will call the API to get the summary
    setTimeout(() => {
        addBotMessage(response);
    }, 500);
}

// Show tracking help
function showTrackingHelp() {
    const helpText = `
        Here's how to track your baby's routine:
        
        Sleep Tracking:
        - "sleep 8:30pm" - Record sleep start
        - "woke 6:15am" - Record wake up
        
        Feeding Tracking:
        - "feed 2:30pm" - Record feeding start
        - "done feeding 2:45pm" - Record feeding end
        
        Summary:
        - "summary today" - Get today's summary
        - "summary week" - Get weekly summary
        - "summary month" - Get monthly summary
    `;
    
    setTimeout(() => {
        addBotMessage(helpText);
    }, 500);
}

// Show typing indicator
function showTypingIndicator() {
    elements.typingIndicator.classList.add('visible');
}

// Hide typing indicator
function hideTypingIndicator() {
    elements.typingIndicator.classList.remove('visible');
}

// Generate a unique thread ID
function generateThreadId() {
    return 'thread_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
}

// Initialize the chat when the page loads
document.addEventListener('DOMContentLoaded', initChat); 