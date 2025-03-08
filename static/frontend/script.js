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

// API base URL
const API_BASE_URL = 'http://localhost:8000';

// API endpoints
const API_ENDPOINTS = {
    CHAT: `${API_BASE_URL}/api/chat`,
    RESET: `${API_BASE_URL}/api/chat/reset`,
    CONTEXT: `${API_BASE_URL}/api/chat/context`,
    ROUTINE_EVENTS: `${API_BASE_URL}/api/routines/events`,
    ROUTINE_SUMMARY: `${API_BASE_URL}/api/routines/summary`,
    ROUTINE_LATEST: `${API_BASE_URL}/api/routines/events/latest`,
    HEALTH: `${API_BASE_URL}/health`,
    ROUTINE_COMMAND: `${API_BASE_URL}/api/routines/command`,
    ROUTINE_PROCESS_COMMAND: `${API_BASE_URL}/api/routines/process-command`
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
    // Handle undefined or null text
    if (!text) {
        return "No response received. Please try again.";
    }
    
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

// Check if a message contains a routine tracking command
function isRoutineCommand(message) {
    // English patterns
    const sleepPatterns = [
        /baby.*sleep/i, /went to sleep/i, /sleeping/i, /nap/i, /woke up/i, 
        /put.*to bed/i, /is awake/i, /slept at/i, /slept from/i, /sleep at/i,
        /woke at/i, /woke from/i, /fell asleep/i
    ];
    
    const feedingPatterns = [
        /feeding/i, /fed/i, /eating/i, /nursing/i, /breastfeeding/i, 
        /bottle/i, /formula/i, /fed at/i, /ate at/i, /nursed at/i
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
    
    const feedingPatternsHe = [
        /האכלה/i, /האכיל/i, /אוכל/i, /הנקה/i, /בקבוק/i,
        /פורמולה/i, /ינק/i, /הניק/i, /האכלתי/i, /אכל/i, /אכלה/i,
        /האכלה ב/i, /האכיל ב/i, /הניקה ב/i, /ינק ב/i
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
    
    // Check if message matches any pattern
    const matchesSleepPattern = [...sleepPatterns, ...sleepPatternsHe].some(pattern => pattern.test(message));
    const matchesFeedPattern = [...feedingPatterns, ...feedingPatternsHe].some(pattern => pattern.test(message));
    const matchesSummaryPattern = [...summaryPatterns, ...summaryPatternsHe].some(pattern => pattern.test(message));
    
    // If it's a summary request, it's definitely a routine command
    if (matchesSummaryPattern) {
        console.log('Detected summary command:', message);
        return true;
    }
    
    // If it has a time pattern and matches a sleep or feed pattern, it's likely a routine command
    if (hasTimePattern && (matchesSleepPattern || matchesFeedPattern)) {
        console.log('Detected routine command with time:', message);
        return true;
    }
    
    // If it strongly matches a sleep or feed pattern, even without a time, consider it a routine command
    if (matchesSleepPattern || matchesFeedPattern) {
        console.log('Detected routine command without explicit time:', message);
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
        } else if (eventType === 'feeding') {
            storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
        } else {
            console.warn(`Unknown event type: ${eventType}, defaulting to feeding`);
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
        } else if (eventType === 'feeding') {
            storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
        } else {
            console.warn(`Unknown event type: ${eventType}, defaulting to feeding`);
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
        } else if (eventType === 'feeding') {
            storageKey = STORAGE_KEYS.FEED_EVENTS + threadId;
        } else {
            console.warn(`Unknown event type: ${eventType}, defaulting to feeding`);
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
            
            // Determine if it's likely a sleep or feed event (simple heuristic)
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
            
            let eventType = 'feeding'; // Default to feeding
            
            if (isSummaryEvent) {
                // Don't create an event for summary requests
                console.log(`Detected summary request: "${message}" for period: ${period}`);
                localEventId = null; // Don't save summary requests as events
                
                // Fetch the summary with the detected period
                setTimeout(() => {
                    fetchRoutineSummary(period);
                }, 500);
            } else if (isSleepEvent) {
                eventType = 'sleep';
                console.log(`Detected sleep start event in message: "${message}"`);
                // Save to localStorage
                localEventId = saveEventToLocalStorage(eventType, eventData);
            } else if (isWakeEvent) {
                // This is a sleep end event, we should find the latest sleep event and update it
                console.log(`Detected sleep end event in message: "${message}"`);
                eventType = 'sleep_end';
                // Save as a special type to handle differently during sync
                localEventId = saveEventToLocalStorage(eventType, eventData);
            } else {
                console.log(`Detected feed event in message: "${message}"`);
                // Save to localStorage
                localEventId = saveEventToLocalStorage(eventType, eventData);
            }
            
            // Check if we're offline and show notification if needed
            if (!isOnline && isRoutineCmd) {
                showOfflineNotification();
            }
        }
        
        // Check server connection before sending
        let serverAvailable = true;
        if (isRoutineCmd) {
            // Only check server for routine commands to avoid extra requests
            serverAvailable = await fetch(API_ENDPOINTS.HEALTH)
                .then(response => response.ok)
                .catch(() => false);
                
            if (!serverAvailable) {
                isOnline = false;
                updateSyncStatus();
                
                // If offline and this is a routine command, show a message
                hideTypingIndicator();
                
                const responseText = language === 'he' ?
                    'הנתונים נשמרו מקומית ויסונכרנו כאשר החיבור לשרת יתחדש.' :
                    'Your data has been saved locally and will sync when server connection is restored.';
                
                addMessage(responseText, false);
                showOfflineNotification();
                return;
            }
        }
        
        // If we get here, we're online
        isOnline = true;
        
        // For routine commands (except summary), use the routine command endpoint
        if (isRoutineCmd && !isSummaryEvent) {
            try {
                // Send the command to the routine command endpoint
                const commandResponse = await fetch(API_ENDPOINTS.ROUTINE_PROCESS_COMMAND, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        thread_id: threadId,
                        language: language
                    })
                });
                
                if (commandResponse.ok) {
                    const commandData = await commandResponse.json();
                    hideTypingIndicator();
                    
                    if (commandData.status === "success" && commandData.response) {
                        // Display the command response
                        addMessage(commandData.response, false);
                        
                        // Sync events after successful command processing
                        await syncLocalEvents();
                        return;
                    }
                }
                // If we get here, either the command failed or wasn't recognized
                // Fall through to the regular chat processing
            } catch (error) {
                console.error('Error processing command:', error);
                // Fall through to regular chat processing
            }
        }
        
        // Regular chat processing for non-commands or fallback
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
        
        if (response.ok) {
            const data = await response.json();
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add bot response to chat
            addMessage(data.text, false);
            
            // Update context information if available
            if (data.context) {
                updateContextInfo(data.context);
            }
            
            // If this was a routine tracking command, check for updates
            if (isRoutineCmd && !isSummaryEvent) { // Don't fetch summary again for summary requests
                // Wait a moment then fetch the latest summary
                setTimeout(() => {
                    fetchRoutineSummary('day');
                }, 1000);
            }
        } else {
            // Handle error response
            hideTypingIndicator();
            const errorMsg = language === 'he' ? 
                'אירעה שגיאה בתקשורת עם השרת. נסה שוב מאוחר יותר.' : 
                'An error occurred communicating with the server. Please try again later.';
            addMessage(errorMsg, false);
            console.error(`API returned ${response.status}`);
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
            console.log('Offline mode: generating local summary');
            displayLocalSummary(period);
            return;
        }
        
        const response = await fetch(`${API_ENDPOINTS.ROUTINE_SUMMARY}/${threadId}?period=${period}`);
        
        if (!response.ok) {
            console.error('Error fetching routine summary');
            
            // If server request fails, generate a summary from local data
            displayLocalSummary(period);
            return;
        }
        
        const data = await response.json();
        
        // Process summary data if needed
        console.log('Routine summary:', data);
        
        // We don't need to display anything here as the chatbot will respond with the summary
        
    } catch (error) {
        console.error('Error fetching routine summary:', error);
        
        // Generate and display a summary from local data
        displayLocalSummary(period);
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
                    summary.period === 'week' ? 'השבוע' : 'החודש';
    } else {
        periodName = summary.period === 'day' ? 'Today' : 
                    summary.period === 'week' ? 'This Week' : 'This Month';
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
            `${API_ENDPOINTS.ROUTINE_EVENTS}?thread_id=${threadId}&start_date=${startDate}&end_date=${endDate}`
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
        
        console.log(`Found ${sleepEvents.length} unsynced sleep events, ${sleepEndEvents.length} unsynced sleep end events, and ${feedEvents.length} unsynced feeding events`);
        
        // Process sleep events
        for (const event of sleepEvents) {
            try {
                console.log(`Syncing sleep event: ${JSON.stringify(event)}`);
                
                // Extract time from the message using regex
                const timeMatch = event.message.match(/(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)/i);
                let eventTime = event.start_time; // Default to the recorded time
                
                if (timeMatch) {
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(timeMatch[1]);
                    if (parsedTime) {
                        eventTime = new Date(parsedTime).toISOString();
                    }
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
                const response = await fetch(API_ENDPOINTS.ROUTINE_EVENTS, {
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
                const timeMatch = event.message.match(/(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)/i);
                let endTime = event.start_time; // Default to the recorded time
                
                if (timeMatch) {
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(timeMatch[1]);
                    if (parsedTime) {
                        endTime = new Date(parsedTime).toISOString();
                    }
                }
                
                // Get the latest sleep event for this thread from the server
                try {
                    const response = await fetch(`${API_ENDPOINTS.ROUTINE_LATEST}/${event.thread_id}/sleep`);
                    
                    if (response.ok) {
                        const latestEvent = await response.json();
                        
                        if (latestEvent && latestEvent.id) {
                            console.log(`Found latest sleep event to update: ${JSON.stringify(latestEvent)}`);
                            
                            // Get the start time of the sleep event
                            let startTime = latestEvent.start_time;
                            if (typeof startTime === 'string') {
                                startTime = new Date(startTime);
                            }
                            
                            // Ensure end time is after start time
                            let endTimeDate = new Date(endTime);
                            
                            // If end time is before or equal to start time, add 1 minute to start time
                            if (endTimeDate <= startTime) {
                                console.log(`End time ${endTimeDate} is not after start time ${startTime}, adjusting...`);
                                endTimeDate = new Date(startTime.getTime() + 60000); // Add 1 minute
                                endTime = endTimeDate.toISOString();
                                console.log(`Adjusted end time to ${endTime}`);
                            }
                            
                            // Update the event with the end time
                            const updateResponse = await fetch(`${API_ENDPOINTS.ROUTINE_EVENTS}/${latestEvent.id}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    end_time: endTime,
                                    notes: latestEvent.notes || `Updated with end time from: ${event.message}`
                                })
                            });
                            
                            if (updateResponse.ok) {
                                console.log(`Successfully updated sleep event ${latestEvent.id} with end time`);
                                markEventAsSynced('sleep_end', event.local_id);
                            } else {
                                const errorText = await updateResponse.text();
                                console.error(`Error updating sleep event, server returned ${updateResponse.status}: ${errorText}`);
                            }
                        } else {
                            console.warn(`No sleep event found to update for thread ${event.thread_id}`);
                            markEventAsSynced('sleep_end', event.local_id);
                        }
                    } else {
                        console.error(`Error fetching latest sleep event: ${response.status}`);
                    }
                } catch (error) {
                    console.error(`Error processing sleep end event ${event.local_id}:`, error);
                }
            } catch (error) {
                console.error(`Error processing sleep end event ${event.local_id}:`, error);
            }
        }
        
        // Process feed events
        for (const event of feedEvents) {
            try {
                console.log(`Syncing feed event: ${JSON.stringify(event)}`);
                
                // Extract time from the message using regex
                const timeMatch = event.message.match(/(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)/i);
                let eventTime = event.start_time; // Default to the recorded time
                
                if (timeMatch) {
                    // Try to parse the time from the message
                    const parsedTime = parseTimeFromString(timeMatch[1]);
                    if (parsedTime) {
                        eventTime = new Date(parsedTime).toISOString();
                    }
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
                const response = await fetch(API_ENDPOINTS.ROUTINE_EVENTS, {
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
        // Normalize the time string
        timeStr = timeStr.toLowerCase().trim();
        
        // Current date
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        // Handle "8:30" format
        if (timeStr.includes(':')) {
            const [hours, minutes] = timeStr.split(':');
            const isPM = timeStr.includes('pm');
            
            let hour = parseInt(hours);
            if (isPM && hour < 12) hour += 12;
            if (!isPM && hour === 12) hour = 0;
            
            return today.setHours(hour, parseInt(minutes));
        }
        
        // Handle simple hour format
        const hour = parseInt(timeStr);
        const isPM = timeStr.includes('pm');
        
        let adjustedHour = hour;
        if (isPM && hour < 12) adjustedHour += 12;
        if (!isPM && hour === 12) adjustedHour = 0;
        
        return today.setHours(adjustedHour, 0);
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