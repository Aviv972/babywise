/**
 * Babywise Assistant - Frontend Script
 * Handles chat functionality and routine tracking
 */

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const typingIndicator = document.getElementById('typing-indicator');
const newChatButton = document.getElementById('new-chat');
const contextInfo = document.getElementById('context-info');
const contextItems = document.getElementById('context-items');
const syncStatus = document.getElementById('sync-status');
const syncIcon = document.getElementById('sync-icon');
const syncText = document.getElementById('sync-text');

// Thread ID for conversation tracking
let threadId = localStorage.getItem('threadId') || generateThreadId();
localStorage.setItem('threadId', threadId);

// Current language (default to English)
let currentLanguage = 'en';

// Track connection status
let isOnline = navigator.onLine;
let isSyncing = false;
let unsyncedCount = 0;
let hasShownOfflineNotice = false;

// Local storage keys
const STORAGE_KEYS = {
    THREAD_ID: 'threadId',
    SLEEP_EVENTS: 'sleepEvents_',
    SLEEP_END_EVENTS: 'sleepEndEvents_',
    FEED_EVENTS: 'feedEvents_',
    LAST_SYNC: 'lastSync_'
};

// API base URL and mode
// Use relative URL for production deployment
const API_BASE_URL = '';  // Empty string means use relative URLs
const USE_SERVER_PY = true; // Set to true if using server.py, false if using uvicorn directly

// API endpoints
const API_ENDPOINTS = {
    // Endpoints using the correct backend routes
    CHAT: `${API_BASE_URL}/api/chat`,
    HEALTH: `${API_BASE_URL}/api/health`,
    REDIS_TEST: `${API_BASE_URL}/api/redis-test`,
    // The following endpoints are not available in the minimal API
    // but we keep them in the code for future implementation
    RESET: `${API_BASE_URL}/api/chat/reset`,
    CONTEXT: `${API_BASE_URL}/api/chat/context`,
    ROUTINES: {
        EVENTS: `${API_BASE_URL}/api/routines/events`,
        SLEEP: `${API_BASE_URL}/api/routines/sleep`,
        FEED: `${API_BASE_URL}/api/routines/feed`,
        SUMMARY: `${API_BASE_URL}/api/routines/summary`
    }
};

// Language detection function
function detectLanguage(text) {
    // Hebrew characters
    if (/[\u0590-\u05FF]/.test(text)) {
        return 'he';
    }
    // Arabic characters
    if (/[\u0600-\u06FF]/.test(text)) {
        return 'ar';
    }
    // Default to English
    return 'en';
}

// Generate a random thread ID
function generateThreadId() {
    return 'thread_' + Math.random().toString(36).substring(2, 15);
}

// Format markdown in messages
function formatMarkdown(text) {
    // Convert markdown to HTML
    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Line breaks
    text = text.replace(/\n/g, '<br>');
    
    // Handle routine tracking summaries with special formatting
    if (text.includes('Baby Routine Summary') || text.includes('סיכום שגרת תינוק')) {
        // Add special styling for summaries
        text = text.replace(/(Baby Routine Summary for .*?)\n/g, '<div class="summary-title">$1</div>');
        text = text.replace(/(סיכום שגרת תינוק .*?)\n/g, '<div class="summary-title">$1</div>');
        text = text.replace(/\*\*Sleep:\*\*/g, '<div class="summary-section">Sleep:</div>');
        text = text.replace(/\*\*שינה:\*\*/g, '<div class="summary-section">שינה:</div>');
        text = text.replace(/\*\*Feeding:\*\*/g, '<div class="summary-section">Feeding:</div>');
        text = text.replace(/\*\*האכלה:\*\*/g, '<div class="summary-section">האכלה:</div>');
    }
    
    return text;
}

// Add a message to the chat
function addMessage(message, isUser = false, isSystem = false) {
    // First remove the typing indicator if it exists in the chat
    if (typingIndicator.parentNode === chatMessages) {
        chatMessages.removeChild(typingIndicator);
    }
    
    const messageDiv = document.createElement('div');
    
    // Check if the message is in a right-to-left language
    const language = detectLanguage(message);
    const isRTL = (language === 'he' || language === 'ar');
    
    if (isSystem) {
        messageDiv.className = 'message system-message';
    } else if (isUser) {
        messageDiv.className = 'message user-message';
        
        if (isRTL) {
            messageDiv.classList.add('rtl');
        }
    } else {
        messageDiv.className = 'message bot-message';
        
        // Format markdown in bot messages
        message = formatMarkdown(message);
        
        if (isRTL) {
            messageDiv.classList.add('rtl');
        }
    }
    
    // Create message content
    const messageContent = document.createElement('span');
    messageContent.innerHTML = message;
    messageDiv.appendChild(messageContent);
    
    // Add timestamp
    if (!isSystem) {
        const timestamp = document.createElement('span');
        timestamp.className = 'timestamp';
        const now = new Date();
        timestamp.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(timestamp);
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Re-append the typing indicator to ensure it's at the end
    chatMessages.appendChild(typingIndicator);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    // First remove the typing indicator from its current position
    if (typingIndicator.parentNode) {
        typingIndicator.parentNode.removeChild(typingIndicator);
    }
    
    // Then append it to the end of the chat messages container
    chatMessages.appendChild(typingIndicator);
    
    // Now display it
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Hide typing indicator
function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// Update context information
function updateContextInfo(context) {
    // We're hiding context info as requested
    contextInfo.style.display = 'none';
    // Skip processing context data since we're not displaying it
    return;
}

// Add new function to detect feeding events with time
function isFeedingEventWithTime(message) {
    // Time patterns
    const timePatterns = [
        /\d{1,2}:\d{2}/i,                    // 8:30, 14:30
        /\d{1,2}(?::\d{2})?\s*(?:am|pm)/i,   // 8am, 2:30pm
        /\d{1,2}(?::\d{2})?\s*(?:בבוקר|בערב|בצהריים|בלילה)/i  // Hebrew times
    ];

    // Feeding action patterns - more specific than general patterns
    const feedingActionPatterns = [
        // English patterns for actual feeding events
        /(?:fed|ate|nursed|had\s+a\s+bottle)\s+at/i,
        /(?:gave|giving)\s+(?:bottle|formula|milk)/i,
        /(?:feeding|nursing|breastfeeding)\s+(?:now|at)/i,
        /(?:bottle|breast)fed\s+at/i,
        
        // Hebrew patterns for actual feeding events
        /האכלתי\s+(?:ב|את)/i,
        /הנקתי\s+(?:ב|את)/i,
        /(?:אכל|ינק|שתה)\s+(?:ב|את)/i,
        /נתתי\s+(?:בקבוק|פורמולה)\s+ב/i
    ];

    const hasTime = timePatterns.some(pattern => pattern.test(message));
    const hasAction = feedingActionPatterns.some(pattern => pattern.test(message));

    return {
        isFeeding: hasAction,
        hasTime: hasTime,
        isQuestion: /(?:how|when|what|why|where|כמה|מתי|איך|למה|איפה)\s+/i.test(message)
    };
}

// Check if a message contains a routine tracking command
function isRoutineCommand(message) {
    // English patterns
    const sleepPatterns = [
        /baby.*sleep/i, /went to sleep/i, /sleeping/i, /nap/i, /woke up/i, 
        /put.*to bed/i, /is awake/i, /slept at/i, /slept from/i, /sleep at/i,
        /woke at/i, /woke from/i, /fell asleep/i
    ];
    
    const summaryPatterns = [
        /summary/i, /report/i, /overview/i, /stats/i, /statistics/i,
        /show me.*summary/i, /show.*report/i, /get.*summary/i
    ];
    
    // Hebrew patterns
    const sleepPatternsHe = [
        /תינוק.*שינה/i, /הלך לישון/i, /ישן/i, /נרדם/i, /התעורר/i,
        /שם.*במיטה/i, /ער/i, /קם/i, /ישן ב/i, /נרדם ב/i, /התעורר ב/i,
        /הלך לישון ב/i, /ישנה/i, /נרדמה/i, /התעוררה/i
    ];
    
    const summaryPatternsHe = [
        /סיכום/i, /דוח/i, /סקירה/i, /סטטיסטיקה/i, /הראה לי סיכום/i,
        /תן לי סיכום/i, /הצג סיכום/i, /הצג דוח/i
    ];
    
    // Time patterns that might indicate a routine event
    const timePatterns = [
        /\d{1,2}:\d{2}/i, // 8:30, 14:30
        /\d{1,2}(?::\d{2})?\s*(?:am|pm)/i, // 8am, 2:30pm
        /\d{1,2}(?::\d{2})?\s*(?:בבוקר|בערב|בצהריים|בלילה)/i // Hebrew time indicators
    ];
    
    // Check if message contains a time pattern and a routine keyword
    const hasTimePattern = timePatterns.some(pattern => pattern.test(message));
    
    // Check if the message matches any of our command patterns
    const matchesSleepPattern = [...sleepPatterns, ...sleepPatternsHe].some(pattern => pattern.test(message));
    const matchesSummaryPattern = [...summaryPatterns, ...summaryPatternsHe].some(pattern => pattern.test(message));
    
    // Check for feeding event with time
    const feedingCheck = isFeedingEventWithTime(message);
    
    // If it's a summary request, it's definitely a routine command
    if (matchesSummaryPattern) {
        console.log('Detected summary command:', message);
        return true;
    }
    
    // If it has a time pattern and matches a sleep pattern, it's likely a routine command
    if (hasTimePattern && matchesSleepPattern) {
        console.log('Detected sleep command with time:', message);
        return true;
    }
    
    // If it's a feeding event with time and not a question, it's a routine command
    if (feedingCheck.isFeeding && feedingCheck.hasTime && !feedingCheck.isQuestion) {
        console.log('Detected feeding command with time:', message);
        return true;
    }
    
    // If it strongly matches a sleep pattern, even without a time, consider it a routine command
    if (matchesSleepPattern) {
        console.log('Detected sleep command without explicit time:', message);
        return true;
    }
    
    console.log('Not a routine command:', message);
    return false;
}

// Update the sync status indicator
function updateSyncStatus() {
    // Count unsynced events
    const unsyncedSleepEvents = getLocalEvents('sleep').filter(event => !event.synced).length;
    const unsyncedSleepEndEvents = getLocalEvents('sleep_end').filter(event => !event.synced).length;
    const unsyncedFeedEvents = getLocalEvents('feeding').filter(event => !event.synced).length;
    unsyncedCount = unsyncedSleepEvents + unsyncedSleepEndEvents + unsyncedFeedEvents;
    
    // Update UI based on status
    if (!isOnline) {
        syncStatus.className = 'offline';
        syncIcon.textContent = '❌';
        syncText.textContent = 'Offline';
        syncStatus.style.display = 'block';
    } else if (isSyncing) {
        syncStatus.className = 'syncing';
        syncIcon.textContent = '🔄';
        syncText.textContent = 'Syncing...';
        syncStatus.style.display = 'block';
    } else if (unsyncedCount > 0) {
        syncStatus.className = 'offline';
        syncIcon.textContent = '⚠️';
        syncText.textContent = `${unsyncedCount} events pending sync`;
        syncStatus.style.display = 'block';
    } else {
        syncStatus.className = 'online';
        syncIcon.textContent = '✅';
        syncText.textContent = 'All data synced';
        
        // Hide after 3 seconds if everything is synced
        syncStatus.style.display = 'block';
        setTimeout(() => {
            if (unsyncedCount === 0 && !isSyncing) {
                syncStatus.style.display = 'none';
            }
        }, 3000);
    }
}

// Modify saveEventToLocalStorage to update sync status
function saveEventToLocalStorage(eventType, eventData) {
    try {
        if (!eventData) return null; // Don't save null events (like summary requests)
        
        console.log(`Saving ${eventType} event to localStorage:`, eventData);
        
        // Get existing events array or create a new one
        let storageKey;
        if (eventType === 'sleep') {
            storageKey = STORAGE_KEYS.SLEEP_EVENTS + threadId;
        } else if (eventType === 'sleep_end') {
            storageKey = STORAGE_KEYS.SLEEP_END_EVENTS + threadId;
        } else {
            storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
        }
        
        let events = JSON.parse(localStorage.getItem(storageKey) || '[]');
        
        // Create a unique local ID
        const localId = `local_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
        
        // Add the new event
        const newEvent = {
            ...eventData,
            local_id: localId,
            synced: false,
            created_at: new Date().toISOString()
        };
        
        events.push(newEvent);
        
        // Save back to localStorage
        localStorage.setItem(storageKey, JSON.stringify(events));
        
        // Update last sync time
        localStorage.setItem(STORAGE_KEYS.LAST_SYNC + threadId, new Date().toISOString());
        
        console.log(`Saved ${eventType} event to localStorage backup with ID: ${localId}`);
        
        // Update sync status indicator
        updateSyncStatus();
        
        return localId;
    } catch (error) {
        console.error('Error saving event to localStorage:', error);
        return null;
    }
}

function getLocalEvents(eventType) {
    try {
        let storageKey;
        
        if (eventType === 'sleep') {
            storageKey = STORAGE_KEYS.SLEEP_EVENTS + threadId;
        } else if (eventType === 'sleep_end') {
            storageKey = STORAGE_KEYS.SLEEP_END_EVENTS + threadId;
        } else {
            storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
        }
        
        return JSON.parse(localStorage.getItem(storageKey) || '[]');
    } catch (error) {
        console.error('Error retrieving events from localStorage:', error);
        return [];
    }
}

// Modify markEventAsSynced to update sync status
function markEventAsSynced(eventType, localId, serverId) {
    try {
        let storageKey;
        
        if (eventType === 'sleep') {
            storageKey = STORAGE_KEYS.SLEEP_EVENTS + threadId;
        } else if (eventType === 'sleep_end') {
            storageKey = STORAGE_KEYS.SLEEP_END_EVENTS + threadId;
        } else {
            storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
        }
        
        let events = JSON.parse(localStorage.getItem(storageKey) || '[]');
        
        // Find and update the event
        const updatedEvents = events.map(event => {
            if (event.local_id === localId) {
                return { ...event, synced: true, server_id: serverId };
            }
            return event;
        });
        
        // Save back to localStorage
        localStorage.setItem(storageKey, JSON.stringify(updatedEvents));
        
        // Update sync status indicator
        updateSyncStatus();
    } catch (error) {
        console.error('Error marking event as synced:', error);
    }
}

function clearOldEvents() {
    try {
        // Keep events for 30 days
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        
        ['sleep', 'sleep_end', 'feeding'].forEach(eventType => {
            let storageKey;
            
            if (eventType === 'sleep') {
                storageKey = STORAGE_KEYS.SLEEP_EVENTS + threadId;
            } else if (eventType === 'sleep_end') {
                storageKey = STORAGE_KEYS.SLEEP_END_EVENTS + threadId;
            } else {
                storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
            }
            
            let events = JSON.parse(localStorage.getItem(storageKey) || '[]');
            
            // Filter out events older than 30 days
            const filteredEvents = events.filter(event => {
                const eventDate = new Date(event.start_time);
                return eventDate > thirtyDaysAgo;
            });
            
            // Save back to localStorage
            localStorage.setItem(storageKey, JSON.stringify(filteredEvents));
        });
    } catch (error) {
        console.error('Error clearing old events:', error);
    }
}

// Show a notification about offline storage
function showOfflineNotification() {
    // Only show this once per session
    if (hasShownOfflineNotice) return;
    
    const message = detectLanguage(userInput.value) === 'he' ?
        'שים לב: הנתונים נשמרים באופן מקומי ויסונכרנו עם השרת כאשר החיבור יתחדש.' :
        'Note: Data is being stored locally and will sync with the server when connection is restored.';
    
    addMessage(message, false, true);
    hasShownOfflineNotice = true;
}

// Modify sendMessage to check connection and show notification
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, true);
    userInput.value = '';
    
    // Detect language
    const language = detectLanguage(message);
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        // Check if this is a routine command
        const isRoutineCmd = isRoutineCommand(message);
        console.log(`Message "${message}" is routine command: ${isRoutineCmd}`);
        
        // If it's a routine command, save it to localStorage as a backup
        let localEventId = null;
        if (isRoutineCmd) {
            // Create a basic event object with the message and timestamp
            const eventData = {
                message: message,
                start_time: new Date().toISOString(),
                thread_id: threadId,
                language: language
            };
            
            // Check for feeding event with time first
            const feedingCheck = isFeedingEventWithTime(message);
            
            // Determine event type based on message content
            const isSleepEvent = message.match(/sleep|nap|bed|ישן|שינה|נרדם/i);
            const isWakeEvent = message.match(/woke|awake|wake|התעורר|ער|קם/i);
            const isSummaryEvent = message.match(/summary|report|overview|stats|statistics|data|סיכום|דוח|סקירה|נתונים|סטטיסטיקה/i);
            
            // Extract period from summary request
            let period = 'day'; // Default to day
            if (isSummaryEvent) {
                if (message.match(/week|שבוע/i)) {
                    period = 'week';
                } else if (message.match(/month|חודש/i)) {
                    period = 'month';
                }
            }
            
            let eventType = null;
            let shouldProcessAsCommand = true;
            
            if (isSummaryEvent) {
                // Don't create an event for summary requests
                console.log(`Detected summary request: "${message}" for period: ${period}`);
                localEventId = null; // Don't save summary requests as events
                shouldProcessAsCommand = true;
                
                // Hide typing indicator since we're handling locally
                hideTypingIndicator();
                
                // Show a temporary message while fetching the summary
                const tempMsg = language === 'he' ? 
                    'מכין סיכום, רגע בבקשה...' : 
                    'Preparing summary, one moment please...';
                addMessage(tempMsg, false);
                
                // We'll let the server handle the summary response
                setTimeout(() => {
                    fetchRoutineSummary(period);
                }, 500);
            } else if (feedingCheck.isFeeding && feedingCheck.hasTime && !feedingCheck.isQuestion) {
                eventType = 'feeding';
                console.log(`Detected feed event with time in message: "${message}"`);
                localEventId = saveEventToLocalStorage(eventType, eventData);
                shouldProcessAsCommand = true;
            } else if (isSleepEvent) {
                eventType = 'sleep';
                console.log(`Detected sleep start event in message: "${message}"`);
                localEventId = saveEventToLocalStorage(eventType, eventData);
                shouldProcessAsCommand = true;
            } else if (isWakeEvent) {
                eventType = 'sleep_end';
                console.log(`Detected sleep end event in message: "${message}"`);
                localEventId = saveEventToLocalStorage(eventType, eventData);
                shouldProcessAsCommand = true;
            }
            
            // Check if we're offline and show notification if needed
            if (!isOnline && isRoutineCmd) {
                showOfflineNotification();
            }
            
            // If this is a command we should process locally, don't send to server for LLM processing
            if (shouldProcessAsCommand) {
                // Hide typing indicator since we're handling locally
                hideTypingIndicator();
                
                // Show appropriate confirmation message
                let confirmationMsg;
                if (language === 'he') {
                    if (eventType === 'sleep') {
                        confirmationMsg = 'רשמתי שהתינוק נרדם.';
                    } else if (eventType === 'sleep_end') {
                        confirmationMsg = 'רשמתי שהתינוק התעורר.';
                    } else if (eventType === 'feeding') {
                        confirmationMsg = 'רשמתי את זמן ההאכלה.';
                    }
                } else {
                    if (eventType === 'sleep') {
                        confirmationMsg = 'Recorded sleep start time.';
                    } else if (eventType === 'sleep_end') {
                        confirmationMsg = 'Recorded wake up time.';
                    } else if (eventType === 'feeding') {
                        confirmationMsg = 'Recorded feeding time.';
                    }
                }
                
                if (confirmationMsg) {
                    addMessage(confirmationMsg, false);
                }
                
                // Try to sync the event
                setTimeout(() => {
                    syncLocalEvents();
                }, 1000);
                
                return;
            }
        }
        
        // Check server connection before sending
        let serverAvailable = true;
        if (isRoutineCmd) {
            serverAvailable = await fetch(API_ENDPOINTS.HEALTH)
                .then(response => response.ok)
                .catch(() => false);
                
            if (!serverAvailable) {
                isOnline = false;
                updateSyncStatus();
                
                hideTypingIndicator();
                
                const responseText = language === 'he' ?
                    'הנתונים נשמרו מקומית ויסונכרנו כאשר החיבור לשרת יתחדש.' :
                    'Your data has been saved locally and will sync when server connection is restored.';
                
                addMessage(responseText, false);
                showOfflineNotification();
                return;
            }
        }
        
        // If we get here, we're online and this is not a command to process locally
        isOnline = true;
        
        const response = await fetch(API_ENDPOINTS.CHAT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                thread_id: threadId,
                language: language,
                local_event_id: localEventId
            })
        });
        
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
        }
        
        // Update sync status
        updateSyncStatus();
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Add bot response to chat
        addMessage(data.response || data.text || "No response received. Please try again.", false);
        
        // Update context information if available
        if (data.context) {
            updateContextInfo(data.context);
        }
        
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        
        // Mark as offline if there was a network error
        isOnline = false;
        updateSyncStatus();
        
        addMessage('Sorry, there was an error processing your request. Please try again.', false);
        
        // If there was an error and this was a routine command, add a note about local backup
        if (isRoutineCommand(message)) {
            const backupMsg = language === 'he' ?
                'הנתונים נשמרו מקומית ויסונכרנו כאשר החיבור לשרת יתחדש.' :
                'Your data has been saved locally and will sync when server connection is restored.';
            
            addMessage(backupMsg, false, true);
            showOfflineNotification();
        }
    }
}

// Modify fetchRoutineSummary function to include local data when server fails
async function fetchRoutineSummary(period = 'day') {
    try {
        // Check if we're offline first
        if (!isOnline) {
            console.log('Offline mode: cannot fetch summary');
            displayLocalSummary(period);
            return;
        }
        
        // Get the current language from the document
        const language = document.documentElement.lang || getCurrentLanguage();
        console.log(`Current language for summary: ${language}`);
        
        // Show typing indicator while fetching summary
        showTypingIndicator();
        
        console.log(`Fetching routine summary for period: ${period}`);
        console.log(`API endpoint: ${API_ENDPOINTS.ROUTINES.SUMMARY}/${threadId}?period=${period}`);
        const response = await fetch(`${API_ENDPOINTS.ROUTINES.SUMMARY}/${threadId}?period=${period}`);
        
        if (!response.ok) {
            console.error(`Error fetching routine summary: ${response.status} ${response.statusText}`);
            
            // Log response details for debugging
            try {
                const errorText = await response.text();
                console.error('Error response:', errorText);
            } catch (e) {
                console.error('Could not read error response text:', e);
            }
            
            hideTypingIndicator();
            
            // Show error message
            const errorMessage = language === 'he' ?
                `שגיאה בקבלת הסיכום (${response.status}). מציג נתונים מקומיים.` :
                `Error fetching summary (${response.status}). Showing local data.`;
            addMessage(errorMessage, false);
            
            // Fall back to local summary if server fails
            displayLocalSummary(period);
            return;
        }
        
        const data = await response.json();
        console.log('Routine summary data received:', data);
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Format and display the summary
        const formattedSummary = formatServerSummary(data, period);
        console.log('Formatted summary to display:', formattedSummary);
        
        // Add the formatted summary as a message
        console.log('Adding summary message to chat');
        addMessage(formattedSummary, false);
        console.log('Summary message added to chat');
        
    } catch (error) {
        console.error('Error fetching routine summary:', error);
        hideTypingIndicator();
        
        // Show error message
        const errorMessage = language === 'he' ?
            `שגיאה בקבלת הסיכום: ${error.message}. מציג נתונים מקומיים.` :
            `Error fetching summary: ${error.message}. Showing local data.`;
        addMessage(errorMessage, false);
        
        // Fall back to local summary if there's an error
        displayLocalSummary(period);
    }
}

// New function to format server summary
function formatServerSummary(data, period) {
    console.log('Formatting server summary data:', data);
    
    // If data is null or undefined, return a message
    if (!data) {
        console.error('Summary data is null or undefined');
        return getCurrentLanguage() === 'he' ? 
            'לא נמצאו נתונים לתקופה זו.' : 
            'No data found for this period.';
    }
    
    // Get the current language from the document
    const language = document.documentElement.lang || getCurrentLanguage();
    const isHebrew = language === 'he';
    console.log(`Formatting summary in language: ${language}`);
    
    // Determine period name based on language
    let periodName;
    if (isHebrew) {
        periodName = period === 'day' ? 'היום' :
            period === 'week' ? '7 הימים האחרונים' : '30 הימים האחרונים';
    } else {
        periodName = period === 'day' ? 'Today' :
            period === 'week' ? 'Last 7 Days' : 'Last 30 Days';
    }
    console.log(`Period name: ${periodName}`);
    
    // Create title
    let summary = isHebrew ?
        `**סיכום שגרת תינוק ${periodName}**\n\n` :
        `**Baby Routine Summary for ${periodName}**\n\n`;
    
    // Add sleep section
    summary += isHebrew ? '**שינה:**\n' : '**Sleep:**\n';
    
    if (data.summary && data.summary.sleep) {
        console.log('Processing sleep summary:', data.summary.sleep);
        const sleepSummary = data.summary.sleep;
        const sleepCount = sleepSummary.count || 0;
        const sleepDuration = sleepSummary.total_duration || 0;
        
        if (isHebrew) {
            summary += `- סך הכל: ${sleepCount} אירועי שינה\n`;
            summary += `- זמן שינה כולל: ${formatDuration(sleepDuration, language)}\n`;
        } else {
            summary += `- Total: ${sleepCount} sleep events\n`;
            summary += `- Total sleep time: ${formatDuration(sleepDuration, language)}\n`;
        }
    } else {
        console.log('No sleep summary data available');
        summary += isHebrew ? '- אין נתוני שינה זמינים\n' : '- No sleep data available\n';
    }
    
    summary += '\n';
    
    // Add feeding section
    summary += isHebrew ? '**האכלה:**\n' : '**Feeding:**\n';
    
    if (data.summary && data.summary.feeding) {
        console.log('Processing feeding summary:', data.summary.feeding);
        const feedingSummary = data.summary.feeding;
        const feedingCount = feedingSummary.count || 0;
        
        if (isHebrew) {
            summary += `- סך הכל: ${feedingCount} אירועי האכלה\n`;
        } else {
            summary += `- Total: ${feedingCount} feeding events\n`;
        }
    } else {
        console.log('No feeding summary data available');
        summary += isHebrew ? '- אין נתוני האכלה זמינים\n' : '- No feeding data available\n';
    }
    
    // Add recent events if available
    if (data.recent_events) {
        console.log('Processing recent events:', data.recent_events);
        summary += '\n';
        summary += isHebrew ? '**אירועים אחרונים:**\n' : '**Recent Events:**\n';
        
        // Add sleep events
        if (data.recent_events.sleep && data.recent_events.sleep.length > 0) {
            console.log('Processing recent sleep events:', data.recent_events.sleep);
            const sleepEvents = data.recent_events.sleep;
            if (isHebrew) {
                summary += '- **שינה:** ';
                sleepEvents.forEach((event, index) => {
                    // Convert UTC time to local time
                    const localTime = new Date(event.start_time);
                    const time = localTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    summary += `${time}${index < sleepEvents.length - 1 ? ', ' : ''}`;
                });
                summary += '\n';
            } else {
                summary += '- **Sleep:** ';
                sleepEvents.forEach((event, index) => {
                    // Convert UTC time to local time
                    const localTime = new Date(event.start_time);
                    const time = localTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    summary += `${time}${index < sleepEvents.length - 1 ? ', ' : ''}`;
                });
                summary += '\n';
            }
        } else {
            console.log('No recent sleep events available');
        }
        
        // Add feeding events
        if (data.recent_events.feeding && data.recent_events.feeding.length > 0) {
            console.log('Processing recent feeding events:', data.recent_events.feeding);
            const feedingEvents = data.recent_events.feeding;
            if (isHebrew) {
                summary += '- **האכלה:** ';
                feedingEvents.forEach((event, index) => {
                    // Convert UTC time to local time
                    const localTime = new Date(event.start_time);
                    const time = localTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    summary += `${time}${index < feedingEvents.length - 1 ? ', ' : ''}`;
                });
                summary += '\n';
            } else {
                summary += '- **Feeding:** ';
                feedingEvents.forEach((event, index) => {
                    // Convert UTC time to local time
                    const localTime = new Date(event.start_time);
                    const time = localTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    summary += `${time}${index < feedingEvents.length - 1 ? ', ' : ''}`;
                });
                summary += '\n';
            }
        } else {
            console.log('No recent feeding events available');
        }
    } else {
        console.log('No recent events data available');
    }
    
    console.log('Final formatted summary:', summary);
    return summary;
}

// Helper function to format duration
function formatDuration(minutes, language) {
    if (!minutes) return language === 'he' ? '0 דקות' : '0 minutes';
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    if (language === 'he') {
        if (hours > 0) {
            return `${hours} שעות ו-${remainingMinutes} דקות`;
        } else {
            return `${remainingMinutes} דקות`;
        }
    } else {
        if (hours > 0) {
            return `${hours} hours and ${remainingMinutes} minutes`;
        } else {
            return `${remainingMinutes} minutes`;
        }
    }
}

// Display a summary from locally stored data
function displayLocalSummary(period = 'day') {
    try {
        const localSummary = generateLocalSummary(period);
        
        // Create a system message with the summary
        addMessage(localSummary, false, true);
        
    } catch (error) {
        console.error('Error displaying local summary:', error);
        
        // Show error message
        const errorMessage = getCurrentLanguage() === 'he' ?
            'אירעה שגיאה בעת הצגת הסיכום. נסה שוב מאוחר יותר.' :
            'An error occurred while displaying the summary. Please try again later.';
        
        addMessage(errorMessage, false, true);
    }
}

// Generate a summary from locally stored data
function generateLocalSummary(period = 'day') {
    try {
        const threadId = getThreadId();
        
        // Get all events from localStorage
        const sleepEvents = getLocalEvents('sleep');
        const feedEvents = getLocalEvents('feeding');
        
        // Calculate date range based on period
        if (period === 'day') {
            startDate = new Date();
            startDate.setHours(0, 0, 0, 0);
        } else if (period === 'week') {
            startDate = new Date();
            startDate.setDate(startDate.getDate() - startDate.getDay()); // Start of week (Sunday)
            startDate.setHours(0, 0, 0, 0);
        } else if (period === 'month') {
            startDate = new Date();
            startDate.setDate(1); // Start of month
            startDate.setHours(0, 0, 0, 0);
        }
        
        const endDate = new Date();
        
        // Filter events by thread and date range
        const filteredSleepEvents = sleepEvents.filter(event => 
            event.thread_id === threadId && 
            new Date(event.start_time) >= startDate && 
            new Date(event.start_time) <= endDate
        );
        
        const filteredFeedEvents = feedEvents.filter(event => 
            event.thread_id === threadId && 
            new Date(event.start_time) >= startDate && 
            new Date(event.start_time) <= endDate
        );
        
        // Create summary object
        const summary = {
            period: period,
            start_date: startDate.toISOString(),
            end_date: endDate.toISOString(),
            sleep: {
                events: filteredSleepEvents,
                count: filteredSleepEvents.length,
                total_duration: 0 // We don't have duration in local events
            },
            feed: {
                events: filteredFeedEvents,
                count: filteredFeedEvents.length,
                total_duration: 0 // We don't have duration in local events
            }
        };
        
        // Determine period name based on language
        let periodName;
        if (getCurrentLanguage() === 'he') {
            periodName = summary.period === 'day' ? 'היום' :
                summary.period === 'week' ? 'השבוע' : 'החודש';
        } else {
            periodName = summary.period === 'day' ? 'Today' :
                summary.period === 'week' ? 'This Week' : 'This Month';
        }
        
        // Format the summary as a string
        let summaryText = getCurrentLanguage() === 'he' ?
            `📊 סיכום שגרת תינוק ל${periodName} (נתונים מקומיים)\n\n` :
            `📊 Baby Routine Summary for ${periodName} (Local Data)\n\n`;
        
        // Add sleep events
        if (getCurrentLanguage() === 'he') {
            summaryText += `🛌 **שינה**: ${summary.sleep.count} אירועים\n`;
            
            if (summary.sleep.count > 0) {
                filteredSleepEvents.forEach((event, index) => {
                    const time = new Date(event.start_time).toLocaleTimeString('he-IL', {hour: '2-digit', minute:'2-digit'});
                    summaryText += `  ${index + 1}. נרדם ב-${time}\n`;
                });
            } else {
                summaryText += `  לא נרשמו אירועי שינה ל${periodName}.\n`;
            }
            
            summaryText += `\n🍼 **האכלה**: ${summary.feed.count} אירועים\n`;
            
            if (summary.feed.count > 0) {
                filteredFeedEvents.forEach((event, index) => {
                    const time = new Date(event.start_time).toLocaleTimeString('he-IL', {hour: '2-digit', minute:'2-digit'});
                    summaryText += `  ${index + 1}. האכלה ב-${time}\n`;
                });
            } else {
                summaryText += `  לא נרשמו אירועי האכלה ל${periodName}.\n`;
            }
        } else {
            summaryText += `🛌 **Sleep**: ${summary.sleep.count} events\n`;
            
            if (summary.sleep.count > 0) {
                filteredSleepEvents.forEach((event, index) => {
                    const time = new Date(event.start_time).toLocaleTimeString('en-US', {hour: 'numeric', minute:'2-digit', hour12: true});
                    summaryText += `  ${index + 1}. Fell asleep at ${time}\n`;
                });
            } else {
                summaryText += `  No sleep events recorded for ${periodName.toLowerCase()}.\n`;
            }
            
            summaryText += `\n🍼 **Feeding**: ${summary.feed.count} events\n`;
            
            if (summary.feed.count > 0) {
                filteredFeedEvents.forEach((event, index) => {
                    const time = new Date(event.start_time).toLocaleTimeString('en-US', {hour: 'numeric', minute:'2-digit', hour12: true});
                    summaryText += `  ${index + 1}. Fed at ${time}\n`;
                });
            } else {
                summaryText += `  No feeding events recorded for ${periodName.toLowerCase()}.\n`;
            }
        }
        
        return summaryText;
    } catch (error) {
        console.error('Error generating local summary:', error);
        return getCurrentLanguage() === 'he' ?
            'אירעה שגיאה בעת יצירת הסיכום. נסה שוב מאוחר יותר.' :
            'An error occurred while generating the summary. Please try again later.';
    }
}

// Format a local summary for display
function formatLocalSummary(summary) {
    const language = document.documentElement.lang || 'en';
    const isHebrew = language === 'he';
    
    // Determine period name based on language
    let periodName;
    if (isHebrew) {
        periodName = summary.period === 'day' ? 'היום' : 
                    summary.period === 'week' ? '7 הימים האחרונים' : '30 הימים האחרונים';
    } else {
        periodName = summary.period === 'day' ? 'Today' : 
                    summary.period === 'week' ? 'Last 7 Days' : 'Last 30 Days';
    }
    
    // Create the header
    let text = isHebrew ?
        `📊 סיכום שגרת תינוק ל${periodName} (נתונים מקומיים)\n\n` :
        `📊 Baby Routine Summary for ${periodName} (Local Data)\n\n`;
    
    // Sleep events
    text += isHebrew ? `**שינה:**\n` : `**Sleep:**\n`;
    
    if (summary.sleep.total_events === 0) {
        text += isHebrew ? `לא נרשמו אירועי שינה.\n\n` : `No sleep events recorded.\n\n`;
    } else {
        text += isHebrew ? 
            `סך הכל אירועי שינה: ${summary.sleep.total_events}\n` :
            `Total sleep events: ${summary.sleep.total_events}\n`;
            
        summary.sleep.events.forEach((event, index) => {
            const time = new Date(event.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            text += isHebrew ?
                `- אירוע שינה ${index + 1}: ${time}\n` :
                `- Sleep event ${index + 1}: ${time}\n`;
        });
        text += '\n';
    }
    
    // Feed events
    text += isHebrew ? `**האכלה:**\n` : `**Feeding:**\n`;
    
    if (summary.feed.total_events === 0) {
        text += isHebrew ? `לא נרשמו אירועי האכלה.\n` : `No feeding events recorded.\n`;
    } else {
        text += isHebrew ?
            `סך הכל אירועי האכלה: ${summary.feed.total_events}\n` :
            `Total feeding events: ${summary.feed.total_events}\n`;
            
        summary.feed.events.forEach((event, index) => {
            const time = new Date(event.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            text += isHebrew ?
                `- אירוע האכלה ${index + 1}: ${time}\n` :
                `- Feeding event ${index + 1}: ${time}\n`;
        });
    }
    
    // Add a note about data persistence
    text += '\n';
    text += isHebrew ?
        `הערה: נתונים אלה יסונכרנו עם השרת כאשר החיבור יתחדש.` :
        `Note: This data will be synced with the server when connection is restored.`;
    
    return text;
}

// Fetch latest routine events
async function fetchLatestEvents() {
    try {
        // Get current date
        const now = new Date();
        const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        
        // Format dates for API
        const startDate = startOfDay.toISOString();
        const endDate = now.toISOString();
        
        const response = await fetch(
            `${API_ENDPOINTS.ROUTINES.EVENTS}?thread_id=${threadId}&start_date=${startDate}&end_date=${endDate}`
        );
        
        if (!response.ok) {
            console.error('Error fetching routine events');
            return;
        }
        
        const data = await response.json();
        
        // Process events data if needed
        console.log('Today\'s routine events:', data);
        
    } catch (error) {
        console.error('Error fetching routine events:', error);
    }
}

// Reset the chat
function resetChat() {
    // Generate a new thread ID
    threadId = generateThreadId();
    localStorage.setItem('threadId', threadId);
    
    // Clear chat messages except for the welcome message
    chatMessages.innerHTML = '';
    
    // Add welcome message
    addMessage('👋 שלום! אני כאן כדי לעזור לך לנהל את שגרת התינוק בקלות, לעקוב אחרי הרגלים חשובים, ולספק תשובות לכל השאלות שלך בדרך להורות בטוחה ורגועה. 😊', false, true);
    addMessage('<p>הנה מה שאני יכול לעשות עבורך:</p>\n\n<p class="category-title">❓ שאלות כלליות</p>\n<p class="indented">את/ה יכול/ה לשאול אותי על שינה, האכלה, התפתחות, ציוד לתינוק ועוד.</p>\n\n<p class="category-title">🍼 מעקב שגרת תינוק</p>\n<p class="command-example">💤 שינה: <span class="command-text">"התינוק נרדם ב-20:00"</span> ← תיעוד זמן שינה</p>\n<p class="command-example">☀️ התעוררות: <span class="command-text">"התינוק התעורר ב-6:00"</span> ← תיעוד סיום שינה</p>\n<p class="command-example">🥣 האכלה: <span class="command-text">"האכלתי את התינוק ב-14:30"</span> ← תיעוד ארוחה</p>\n<p class="command-example">📊 סיכום יומי: <span class="command-text">"הראה לי סיכום של היום"</span> ← קבלת דוח יומי</p>\n\n<p class="closing">איך אוכל לעזור לך היום? 😊</p>', false);
    
    // Add typing indicator back to the chat messages
    chatMessages.appendChild(typingIndicator);
    
    // Clear context info (keeping this hidden)
    contextInfo.style.display = 'none';
    
    // Reset the chat on the server
    fetch(API_ENDPOINTS.RESET, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            thread_id: threadId
        })
    }).catch(error => {
        console.error('Error resetting chat:', error);
    });
}

// Check for context from server periodically
async function checkContext() {
    try {
        const response = await fetch(`${API_ENDPOINTS.CONTEXT}/${threadId}`);
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.context) {
            updateContextInfo(data.context);
        }
    } catch (error) {
        console.error('Error checking context:', error);
    }
}

// Modify syncLocalEvents to update sync status
async function syncLocalEvents() {
    if (!isOnline || isSyncing) return;
    
    try {
        isSyncing = true;
        updateSyncStatus();
        
        console.log('Attempting to sync local events with server...');
        
        const sleepEvents = getLocalEvents('sleep').filter(event => !event.synced);
        const sleepEndEvents = getLocalEvents('sleep_end').filter(event => !event.synced);
        const feedEvents = getLocalEvents('feeding').filter(event => !event.synced);
        
        console.log(`Found ${sleepEvents.length} unsynced sleep events, ${sleepEndEvents.length} unsynced sleep end events, and ${feedEvents.length} unsynced feed events`);
        
        // Process sleep events
        for (const event of sleepEvents) {
            try {
                console.log(`Syncing sleep event: ${JSON.stringify(event)}`);
                
                // Extract time from the message using regex
                // Hebrew pattern: ב-7:30 or ב7:30
                const hebrewTimeMatch = event.message.match(/ב-?(\d{1,2}:\d{2})/);
                // English pattern: at 7:30 or 7:30 am/pm
                const englishTimeMatch = event.message.match(/(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)/i);
                
                let eventTime = event.start_time; // Default to the recorded time
                
                if (hebrewTimeMatch) {
                    console.log(`Found Hebrew time in message: ${hebrewTimeMatch[1]}`);
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(hebrewTimeMatch[1]);
                    if (parsedTime) {
                        // Create a UTC date with the same local time
                        const localHours = parsedTime.getHours();
                        const localMinutes = parsedTime.getMinutes();
                        
                        // Create a new date with the correct UTC time
                        const utcDate = new Date();
                        utcDate.setUTCHours(localHours, localMinutes, 0, 0);
                        
                        eventTime = utcDate.toISOString();
                        console.log(`Parsed Hebrew time to local: ${parsedTime.toLocaleString()}`);
                        console.log(`Converted to UTC: ${utcDate.toUTCString()}`);
                        console.log(`Final ISO string: ${eventTime}`);
                    }
                } else if (englishTimeMatch) {
                    console.log(`Found English time in message: ${englishTimeMatch[1]}`);
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(englishTimeMatch[1]);
                    if (parsedTime) {
                        // Create a UTC date with the same local time
                        const localHours = parsedTime.getHours();
                        const localMinutes = parsedTime.getMinutes();
                        
                        // Create a new date with the correct UTC time
                        const utcDate = new Date();
                        utcDate.setUTCHours(localHours, localMinutes, 0, 0);
                        
                        eventTime = utcDate.toISOString();
                        console.log(`Parsed English time to local: ${parsedTime.toLocaleString()}`);
                        console.log(`Converted to UTC: ${utcDate.toUTCString()}`);
                        console.log(`Final ISO string: ${eventTime}`);
                    }
                } else {
                    console.log(`No time pattern found in message: "${event.message}"`);
                }
                
                // Create event payload
                const payload = {
                    thread_id: event.thread_id,
                    event_type: 'sleep',
                    start_time: eventTime,
                    notes: `Auto-synced from local storage: ${event.message}`
                };
                
                console.log(`Sending sleep event to server: ${JSON.stringify(payload)}`);
                
                // Send to server
                const response = await fetch(API_ENDPOINTS.ROUTINES.EVENTS, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log(`Server response for sleep event: ${JSON.stringify(data)}`);
                    
                    // Mark as synced in localStorage
                    markEventAsSynced('sleep', event.local_id, data.event_id);
                    console.log(`Successfully synced sleep event: ${event.local_id}`);
                } else {
                    const errorText = await response.text();
                    console.error(`Error syncing sleep event, server returned ${response.status}: ${errorText}`);
                }
            } catch (error) {
                console.error(`Error syncing sleep event ${event.local_id}:`, error);
            }
        }
        
        // Process sleep end events
        for (const event of sleepEndEvents) {
            try {
                console.log(`Syncing sleep end event: ${JSON.stringify(event)}`);
                
                // Extract time from the message using regex
                // Hebrew pattern: ב-7:30 or ב7:30
                const hebrewTimeMatch = event.message.match(/ב-?(\d{1,2}:\d{2})/);
                // English pattern: at 7:30 or 7:30 am/pm
                const englishTimeMatch = event.message.match(/(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)/i);
                
                let endTime = event.start_time; // Default to the recorded time
                
                if (hebrewTimeMatch) {
                    console.log(`Found Hebrew time in message: ${hebrewTimeMatch[1]}`);
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(hebrewTimeMatch[1]);
                    if (parsedTime) {
                        // Create a UTC date with the same local time
                        const localHours = parsedTime.getHours();
                        const localMinutes = parsedTime.getMinutes();
                        
                        // Create a new date with the correct UTC time
                        const utcDate = new Date();
                        utcDate.setUTCHours(localHours, localMinutes, 0, 0);
                        
                        endTime = utcDate.toISOString();
                        console.log(`Parsed Hebrew time to local: ${parsedTime.toLocaleString()}`);
                        console.log(`Converted to UTC: ${utcDate.toUTCString()}`);
                        console.log(`Final ISO string: ${endTime}`);
                    }
                } else if (englishTimeMatch) {
                    console.log(`Found English time in message: ${englishTimeMatch[1]}`);
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(englishTimeMatch[1]);
                    if (parsedTime) {
                        // Create a UTC date with the same local time
                        const localHours = parsedTime.getHours();
                        const localMinutes = parsedTime.getMinutes();
                        
                        // Create a new date with the correct UTC time
                        const utcDate = new Date();
                        utcDate.setUTCHours(localHours, localMinutes, 0, 0);
                        
                        endTime = utcDate.toISOString();
                        console.log(`Parsed English time to local: ${parsedTime.toLocaleString()}`);
                        console.log(`Converted to UTC: ${utcDate.toUTCString()}`);
                        console.log(`Final ISO string: ${endTime}`);
                    }
                } else {
                    console.log(`No time pattern found in message: "${event.message}"`);
                }
                
                // Create a new sleep_end event instead of updating a sleep event
                try {
                    const eventData = {
                        thread_id: event.thread_id,
                        event_type: "sleep_end",
                        start_time: endTime,
                        notes: `Auto-synced from local storage: ${event.message}`
                    };
                    
                    console.log(`Sending sleep_end event to server: ${JSON.stringify(eventData)}`);
                    
                    const response = await fetch(API_ENDPOINTS.ROUTINES.EVENTS, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(eventData)
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log(`Server response for sleep_end event: ${JSON.stringify(data)}`);
                        markEventAsSynced('sleep_end', event.local_id, data.event_id);
                        console.log(`Successfully synced sleep_end event: ${event.local_id}`);
                    } else {
                        const errorText = await response.text();
                        console.error(`Error syncing sleep_end event, server returned ${response.status}: ${errorText}`);
                    }
                } catch (error) {
                    console.error(`Error syncing sleep_end event ${event.local_id}:`, error);
                }
            } catch (error) {
                console.error(`Error processing sleep_end event ${event.local_id}:`, error);
            }
        }
        
        // Process feed events
        for (const event of feedEvents) {
            try {
                console.log(`Syncing feed event: ${JSON.stringify(event)}`);
                
                // Extract time from the message using regex
                // Hebrew pattern: ב-7:30 or ב7:30
                const hebrewTimeMatch = event.message.match(/ב-?(\d{1,2}:\d{2})/);
                // English pattern: at 7:30 or 7:30 am/pm
                const englishTimeMatch = event.message.match(/(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)/i);
                
                let eventTime = event.start_time; // Default to the recorded time
                
                if (hebrewTimeMatch) {
                    console.log(`Found Hebrew time in message: ${hebrewTimeMatch[1]}`);
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(hebrewTimeMatch[1]);
                    if (parsedTime) {
                        // Create a UTC date with the same local time
                        const localHours = parsedTime.getHours();
                        const localMinutes = parsedTime.getMinutes();
                        
                        // Create a new date with the correct UTC time
                        const utcDate = new Date();
                        utcDate.setUTCHours(localHours, localMinutes, 0, 0);
                        
                        eventTime = utcDate.toISOString();
                        console.log(`Parsed Hebrew time to local: ${parsedTime.toLocaleString()}`);
                        console.log(`Converted to UTC: ${utcDate.toUTCString()}`);
                        console.log(`Final ISO string: ${eventTime}`);
                    }
                } else if (englishTimeMatch) {
                    console.log(`Found English time in message: ${englishTimeMatch[1]}`);
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(englishTimeMatch[1]);
                    if (parsedTime) {
                        // Create a UTC date with the same local time
                        const localHours = parsedTime.getHours();
                        const localMinutes = parsedTime.getMinutes();
                        
                        // Create a new date with the correct UTC time
                        const utcDate = new Date();
                        utcDate.setUTCHours(localHours, localMinutes, 0, 0);
                        
                        eventTime = utcDate.toISOString();
                        console.log(`Parsed English time to local: ${parsedTime.toLocaleString()}`);
                        console.log(`Converted to UTC: ${utcDate.toUTCString()}`);
                        console.log(`Final ISO string: ${eventTime}`);
                    }
                } else {
                    console.log(`No time pattern found in message: "${event.message}"`);
                }
                
                // Create event payload
                const payload = {
                    thread_id: event.thread_id,
                    event_type: 'feeding',
                    start_time: eventTime,
                    notes: `Auto-synced from local storage: ${event.message}`
                };
                
                console.log(`Sending feed event to server: ${JSON.stringify(payload)}`);
                
                // Send to server
                const response = await fetch(API_ENDPOINTS.ROUTINES.EVENTS, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log(`Server response for feed event: ${JSON.stringify(data)}`);
                    
                    // Mark as synced in localStorage
                    markEventAsSynced('feeding', event.local_id, data.event_id);
                    console.log(`Successfully synced feed event: ${event.local_id}`);
                } else {
                    const errorText = await response.text();
                    console.error(`Error syncing feed event, server returned ${response.status}: ${errorText}`);
                }
            } catch (error) {
                console.error(`Error syncing feed event ${event.local_id}:`, error);
            }
        }
        
        console.log('Sync completed');
        
        // Update sync status
        isSyncing = false;
        updateSyncStatus();
        
        // Trigger a manual sync status update after a short delay
        setTimeout(updateSyncStatus, 1000);
    } catch (error) {
        console.error('Error during sync process:', error);
        isSyncing = false;
        updateSyncStatus();
    }
}

// Helper function to parse time from a string
function parseTimeFromString(timeStr) {
    try {
        console.log(`Parsing time from string: "${timeStr}"`);
        
        // Normalize the time string
        timeStr = timeStr.toLowerCase().trim();
        
        // Current date
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        // Handle Hebrew time format (e.g., "7:30")
        if (timeStr.match(/^\d{1,2}:\d{2}$/)) {
            console.log(`Detected Hebrew/standard time format: ${timeStr}`);
            const [hours, minutes] = timeStr.split(':');
            const hour = parseInt(hours);
            const minute = parseInt(minutes);
            
            // Create a date object with the local time
            const date = new Date();
            date.setHours(hour, minute, 0, 0);
            console.log(`Parsed local time: ${date.toLocaleString()}`);
            
            return date;
        }
        
        // Handle "8:30 am/pm" format
        if (timeStr.includes(':') && (timeStr.includes('am') || timeStr.includes('pm'))) {
            console.log(`Detected time with AM/PM: ${timeStr}`);
            const timeParts = timeStr.match(/(\d{1,2}):(\d{2})\s*(am|pm)/i);
            if (timeParts) {
                let hour = parseInt(timeParts[1]);
                const minute = parseInt(timeParts[2]);
                const isPM = timeParts[3].toLowerCase() === 'pm';
                
                if (isPM && hour < 12) hour += 12;
                if (!isPM && hour === 12) hour = 0;
                
                // Create a date object with the local time
                const date = new Date();
                date.setHours(hour, minute, 0, 0);
                console.log(`Parsed local time with AM/PM: ${date.toLocaleString()}`);
                
                return date;
            }
        }
        
        // Handle simple hour format with am/pm
        const hourMatch = timeStr.match(/(\d{1,2})\s*(am|pm)/i);
        if (hourMatch) {
            console.log(`Detected simple hour with AM/PM: ${timeStr}`);
            let hour = parseInt(hourMatch[1]);
            const isPM = hourMatch[2].toLowerCase() === 'pm';
            
            if (isPM && hour < 12) hour += 12;
            if (!isPM && hour === 12) hour = 0;
            
            // Create a date object with the local time
            const date = new Date();
            date.setHours(hour, 0, 0, 0);
            console.log(`Parsed simple hour with AM/PM: ${date.toLocaleString()}`);
            
            return date;
        }
        
        // Handle simple hour format without am/pm (assume 24-hour format)
        const simpleHourMatch = timeStr.match(/^(\d{1,2})$/);
        if (simpleHourMatch) {
            console.log(`Detected simple hour without AM/PM: ${timeStr}`);
            const hour = parseInt(simpleHourMatch[1]);
            
            // Create a date object with the local time
            const date = new Date();
            date.setHours(hour, 0, 0, 0);
            console.log(`Parsed simple hour: ${date.toLocaleString()}`);
            
            return date;
        }
        
        console.warn(`Could not parse time from string: "${timeStr}"`);
        return null;
    } catch (error) {
        console.error('Error parsing time:', error);
        return null;
    }
}

// Add a function to manually trigger sync
function manualSync() {
    console.log('Manual sync triggered by user');
    
    // Don't try to sync if already syncing
    if (isSyncing) {
        console.log('Already syncing, ignoring manual sync request');
        return;
    }
    
    // Show a message to the user
    const language = document.documentElement.lang || 'en';
    const syncMessage = language === 'he' ?
        'מסנכרן נתונים עם השרת...' :
        'Syncing data with server...';
    
    addMessage(syncMessage, false, true);
    
    // Trigger sync
    syncLocalEvents();
}

// Event listeners
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

newChatButton.addEventListener('click', resetChat);

// Add click event to sync status indicator to manually trigger sync
syncStatus.addEventListener('click', () => {
    // Only allow manual sync if there are unsynced events and we're not already syncing
    if (unsyncedCount > 0 && !isSyncing) {
        manualSync();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check context every 30 seconds
    setInterval(checkContext, 30000);
    
    // Initial context check
    checkContext();
    
    // Clean up old events once a day
    setInterval(clearOldEvents, 24 * 60 * 60 * 1000);
    
    // Initial cleanup
    clearOldEvents();
    
    // Try to sync local events with server every 5 minutes
    setInterval(syncLocalEvents, 5 * 60 * 1000);
    
    // Initial sync attempt
    setTimeout(syncLocalEvents, 5000);
    
    // Initial sync status update
    updateSyncStatus();
    
    // Listen for online/offline events
    window.addEventListener('online', () => {
        console.log('App is online');
        isOnline = true;
        updateSyncStatus();
        // Try to sync when we come back online
        syncLocalEvents();
    });
    
    window.addEventListener('offline', () => {
        console.log('App is offline');
        isOnline = false;
        updateSyncStatus();
    });
    
    // Focus on input field
    userInput.focus();
});

// Helper functions for thread ID and language
function getThreadId() {
    return threadId;
}

function getCurrentLanguage() {
    return currentLanguage;
}

function setCurrentLanguage(language) {
    currentLanguage = language;
} 