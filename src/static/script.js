document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const submitButton = chatForm.querySelector('button');
    const typingIndicator = document.getElementById('typing-indicator');
    const disclaimerModal = document.getElementById('disclaimerModal');
    const agreeButton = document.getElementById('agreeButton');
    const newChatButton = document.getElementById('newChatButton');
    
    let awaitingAnswer = false;
    let currentField = null;
    let lastMessageGroup = null;
    const DEBUG_MODE = true; // Add debug mode flag

    // Persistent Context Management System
    const CONTEXT_VERSION = '1.0';
    const CONTEXT_STORAGE_KEY = 'persistentContext';
    
    // Initialize persistent context with versioning and safety checks
    function initializePersistentContext() {
        try {
            const storedContext = localStorage.getItem(CONTEXT_STORAGE_KEY);
            if (storedContext) {
                const parsed = JSON.parse(storedContext);
                // Version check for future compatibility
                if (parsed.version === CONTEXT_VERSION) {
                    return parsed;
                }
            }
        } catch (e) {
            console.error('Error initializing persistent context:', e);
        }
        
        // Return fresh context if none exists or version mismatch
        return {
            version: CONTEXT_VERSION,
            demographics: {},
            preferences: {},
            history: {},
            lastUpdated: new Date().toISOString(),
            relevanceScores: {}
        };
    }

    // Update persistent context with new information
    function updatePersistentContext(category, field, value, confidence = 1.0) {
        try {
            const context = initializePersistentContext();
            
            // Don't update if the confidence is too low
            if (confidence < 0.3) {
                console.log(`Skipping low confidence update for ${category}.${field}: ${confidence}`);
                return false;
            }

            // Create category if it doesn't exist
            if (!context[category]) {
                context[category] = {};
            }

            // Update the field with metadata
            context[category][field] = {
                value: value,
                timestamp: new Date().toISOString(),
                confidence: confidence,
                updateCount: (context[category][field]?.updateCount || 0) + 1
            };

            // Update last modified timestamp
            context.lastUpdated = new Date().toISOString();

            // Store back to localStorage
            localStorage.setItem(CONTEXT_STORAGE_KEY, JSON.stringify(context));
            
            if (DEBUG_MODE) {
                console.log(`Updated persistent context: ${category}.${field}`, {
                    value,
                    confidence,
                    context
                });
            }
            
            return true;
        } catch (e) {
            console.error('Error updating persistent context:', e);
            return false;
        }
    }

    // Get relevant context for the current query
    function getRelevantPersistentContext(query) {
        try {
            const context = initializePersistentContext();
            const relevantInfo = {};
            
            // Calculate query relevance for each piece of stored context
            Object.entries(context).forEach(([category, fields]) => {
                if (category === 'version' || category === 'lastUpdated') return;
                
                Object.entries(fields).forEach(([field, data]) => {
                    const relevance = calculateContextRelevance(query, category, field, data);
                    if (relevance > 0.4) { // Threshold for inclusion
                        if (!relevantInfo[category]) {
                            relevantInfo[category] = {};
                        }
                        relevantInfo[category][field] = {
                            ...data,
                            relevance
                        };
                    }
                });
            });
            
            if (DEBUG_MODE) {
                console.log('Retrieved relevant persistent context:', relevantInfo);
            }
            
            return relevantInfo;
        } catch (e) {
            console.error('Error getting relevant persistent context:', e);
            return {};
        }
    }

    // Calculate relevance of stored context to current query
    function calculateContextRelevance(query, category, field, data) {
        const now = new Date();
        const timestamp = new Date(data.timestamp);
        const hoursSinceUpdate = (now - timestamp) / (1000 * 60 * 60);
        
        // Time decay factor (24-hour decay)
        const timeFactor = Math.max(0, 1 - (hoursSinceUpdate / 24));
        
        // Confidence factor
        const confidenceFactor = data.confidence || 0.5;
        
        // Usage factor (more frequently updated fields are considered more reliable)
        const usageFactor = Math.min(1, (data.updateCount || 1) / 5);
        
        // Category weight based on type
        const categoryWeights = {
            demographics: 1.2,  // High importance for demographic info
            preferences: 1.0,
            history: 0.8
        };
        
        const categoryWeight = categoryWeights[category] || 1.0;
        
        // Calculate final relevance score
        const relevance = (
            timeFactor * 0.3 +
            confidenceFactor * 0.4 +
            usageFactor * 0.3
        ) * categoryWeight;
        
        return Math.min(1, Math.max(0, relevance));
    }

    // Clean up old or irrelevant context
    function cleanupPersistentContext() {
        try {
            const context = initializePersistentContext();
            const now = new Date();
            let cleaned = false;
            
            Object.entries(context).forEach(([category, fields]) => {
                if (category === 'version' || category === 'lastUpdated') return;
                
                Object.entries(fields).forEach(([field, data]) => {
                    const timestamp = new Date(data.timestamp);
                    const hoursSinceUpdate = (now - timestamp) / (1000 * 60 * 60);
                    
                    // Remove if older than 72 hours or confidence is very low
                    if (hoursSinceUpdate > 72 || data.confidence < 0.2) {
                        delete context[category][field];
                        cleaned = true;
                    }
                });
                
                // Remove empty categories
                if (Object.keys(fields).length === 0) {
                    delete context[category];
                    cleaned = true;
                }
            });
            
            if (cleaned) {
                context.lastUpdated = now.toISOString();
                localStorage.setItem(CONTEXT_STORAGE_KEY, JSON.stringify(context));
                if (DEBUG_MODE) {
                    console.log('Cleaned up persistent context:', context);
                }
            }
        } catch (e) {
            console.error('Error cleaning up persistent context:', e);
        }
    }

    // Context Management System
    const contextExtractors = {
        // Demographic information
        demographics: {
            patterns: {
                baby_name: [
                    {
                        pattern: /\b(?:my|our) baby(?:'s| is)? (?:name is |called )?([A-Za-z]+)\b/i,
                        extract: (match) => ({
                            value: match[1],
                            normalized: match[1].trim(),
                            type: 'name'
                        })
                    },
                    {
                        pattern: /\b(?:name is |called |named )([A-Za-z]+)\b/i,
                        extract: (match) => ({
                            value: match[1],
                            normalized: match[1].trim(),
                            type: 'name'
                        })
                    }
                ],
                baby_age: [
                    {
                        pattern: /(\d+)\s*(month|months|week|weeks|year|years)\s*old/i,
                        extract: (match) => ({
                            value: match[0],
                            unit: match[2],
                            number: parseInt(match[1]),
                            normalized: `${match[1]} ${match[2]}`
                        })
                    },
                    {
                        pattern: /my baby is (\d+)\s*(month|months|week|weeks|year|years)/i,
                        extract: (match) => ({
                            value: match[0],
                            unit: match[2],
                            number: parseInt(match[1]),
                            normalized: `${match[1]} ${match[2]}`
                        })
                    }
                ],
                baby_gender: [
                    /\b(boy|girl|son|daughter)\b/i,
                    /\bmy (boy|girl|son|daughter)\b/i,
                    /\b(he|she) is \d+/i
                ],
                multiple_babies: [
                    /\b(twins|triplets)\b/i,
                    /\bboth babies\b/i
                ]
            },
            weight: 1.2,
            required: ['baby_age'],  // Keep baby_age as required
            confidence_modifiers: {
                explicit_statement: 0.2,    // "My baby's name is John"
                contextual_mention: -0.1,   // "thinking of naming"
                multiple_mentions: 0.15,    // Multiple mentions in same message
                uncertainty: -0.2,          // "might name"
                temporal_markers: 0.1       // "currently named"
            }
        },
        
        // Sleep related information
        sleep: {
            patterns: {
                sleep_schedule: [
                    /(\d+)\s*(nap|naps|hour|hours)\s*(a|per)?\s*day/i,
                    /sleep[s]?\s*(through|for|about)\s*(\d+)/i,
                    /wake[s]?\s*up\s*(every|after|around)\s*(\d+)/i
                ],
                sleep_issues: [
                    /trouble\s*(sleeping|falling asleep|staying asleep)/i,
                    /won't\s*(sleep|nap|stay asleep)/i,
                    /sleep\s*(training|regression)/i
                ],
                sleep_environment: [
                    /\b(crib|bassinet|bed|room|nursery)\b/i,
                    /\b(dark|light|noise|quiet)\b/i
                ]
            },
            weight: 1.0
        },
        
        // Feeding related information
        feeding: {
            patterns: {
                feeding_type: [
                    {
                        pattern: /(breast|formula|bottle|nursing|pumping|milk)\s*(fed|feed|feeding|eat|eating)?/i,
                        extract: (match) => ({
                            value: match[0],
                            type: match[1].toLowerCase(),
                            action: match[2] ? match[2].toLowerCase() : null,
                            normalized: match[0].toLowerCase()
                        })
                    },
                    {
                        pattern: /(fed|feed|feeding|eat|eating)\s*(with|on)?\s*(breast|formula|bottle|milk)/i,
                        extract: (match) => ({
                            value: match[0],
                            type: match[3].toLowerCase(),
                            action: match[1].toLowerCase(),
                            normalized: `${match[3].toLowerCase()} ${match[1].toLowerCase()}`
                        })
                    }
                ],
                feeding_schedule: [
                    {
                        pattern: /(\d+)\s*(time|times|hour|hours)\s*(a|per)?\s*day/i,
                        extract: (match) => ({
                            value: match[0],
                            frequency: parseInt(match[1]),
                            unit: match[2].toLowerCase(),
                            normalized: `${match[1]} ${match[2]} per day`
                        })
                    },
                    {
                        pattern: /every\s*(\d+)\s*(hour|hours)/i,
                        extract: (match) => ({
                            value: match[0],
                            interval: parseInt(match[1]),
                            unit: match[2].toLowerCase(),
                            normalized: `every ${match[1]} ${match[2]}`
                        })
                    },
                    {
                        pattern: /(\d+)\s*(ounce|ounces|oz)/i,
                        extract: (match) => ({
                            value: match[0],
                            amount: parseInt(match[1]),
                            unit: match[2].toLowerCase(),
                            normalized: `${match[1]} ${match[2]}`
                        })
                    }
                ],
                feeding_issues: [
                    {
                        pattern: /(refusing|won't|not|doesn't)\s*(eat|drink|feed|nurse|take|finish)/i,
                        extract: (match) => ({
                            value: match[0],
                            issue_type: 'refusal',
                            action: match[2].toLowerCase(),
                            normalized: `refusing to ${match[2]}`
                        })
                    },
                    {
                        pattern: /(feeding|eating)\s*(problem|issue|concern|difficulty)/i,
                        extract: (match) => ({
                            value: match[0],
                            issue_type: 'general',
                            category: match[2].toLowerCase(),
                            normalized: `${match[1]} ${match[2]}`
                        })
                    },
                    {
                        pattern: /\b(spit|spitting|vomit|vomiting)\b/i,
                        extract: (match) => ({
                            value: match[0],
                            issue_type: 'digestive',
                            action: match[1].toLowerCase(),
                            normalized: match[1].toLowerCase()
                        })
                    }
                ]
            },
            weight: 1.0,
            confidence_modifiers: {
                explicit_statement: 0.2,    // "My baby drinks formula"
                contextual_mention: -0.1,   // "thinking about switching to formula"
                multiple_mentions: 0.15,    // Multiple mentions in same message
                uncertainty: -0.2,          // "might try formula"
                temporal_markers: 0.1       // "currently breastfeeding"
            }
        },
        
        // Health related information
        health: {
            patterns: {
                symptoms: [
                    /\b(fever|cough|cold|sick|rash)\b/i,
                    /\b(diarrhea|constipation|vomiting)\b/i,
                    /\b(crying|fussy|irritable)\b/i
                ],
                medications: [
                    /\b(medicine|medication|tylenol|ibuprofen)\b/i,
                    /\b(drops|syrup|prescription)\b/i
                ],
                medical_history: [
                    /\b(doctor|pediatrician|hospital|clinic)\b/i,
                    /\b(vaccin|shot|immunization)\b/i,
                    /\b(allerg|reaction)\b/i
                ]
            },
            weight: 1.2
        },
        
        // Development related information
        development: {
            patterns: {
                milestones: [
                    /\b(crawl|walk|talk|roll|sit)\b/i,
                    /\b(milestone|development|skill)\b/i,
                    /\b(teeth|teething|tooth)\b/i
                ],
                concerns: [
                    /\b(worry|concerned|delayed|behind)\b/i,
                    /\b(normal|typical|average)\b/i,
                    /should\s*(be|start)\s*(doing|walking|talking)/i
                ],
                activities: [
                    /\b(play|activity|exercise|tummy time)\b/i,
                    /\b(read|sing|music|toys)\b/i
                ]
            },
            weight: 0.8
        }
    };

    function identifyTopics(content) {
        if (!content || typeof content !== 'string') return [];
        
        const text = content.toLowerCase();
        const topics = new Set();
        
        if (DEBUG_MODE) {
            console.group('Topic Identification');
            console.log('Processing text:', text);
        }
        
        // Check each category's patterns
        Object.entries(contextExtractors).forEach(([category, config]) => {
            if (DEBUG_MODE) {
                console.group(`Category: ${category}`);
            }
            
            Object.entries(config.patterns).forEach(([subType, patterns]) => {
                if (Array.isArray(patterns)) {
                    const hasMatch = patterns.some(pattern => {
                        if (pattern instanceof RegExp) {
                            const matches = pattern.test(text);
                            if (DEBUG_MODE && matches) {
                                console.log(`Match found in ${category}.${subType} with RegExp pattern:`, pattern);
                            }
                            return matches;
                        } else if (pattern && typeof pattern === 'object' && pattern.pattern) {
                            const matches = pattern.pattern.test(text);
                            if (DEBUG_MODE && matches) {
                                console.log(`Match found in ${category}.${subType} with structured pattern:`, pattern.pattern);
                            }
                            return matches;
                        }
                        return false;
                    });
                    if (hasMatch) {
                        topics.add(category);
                        if (DEBUG_MODE) {
                            console.log(`Added topic: ${category}`);
                        }
                    }
                }
            });
            
            if (DEBUG_MODE) {
                console.groupEnd();
            }
        });
        
        if (DEBUG_MODE) {
            console.log('Identified topics:', Array.from(topics));
            console.groupEnd();
        }
        
        return Array.from(topics);
    }

    function calculateMessageRelevance(message, currentQuery) {
        if (!message || !currentQuery || !message.data || !message.data.text) {
            console.log('Invalid message or query for relevance calculation:', { message, currentQuery });
            return 0;
        }

        // Time relevance: newer messages are more relevant
        const timeRelevance = (() => {
            const msgTime = new Date(message.timestamp).getTime();
            const now = Date.now();
            const hoursDiff = (now - msgTime) / (1000 * 60 * 60);
            return Math.max(0, 1 - (hoursDiff / 24)); // Decay over 24 hours
        })();

        // Topic relevance: messages about the same topic are more relevant
        const topicRelevance = (() => {
            const messageTopics = identifyTopics(message.data.text);
            const queryTopics = identifyTopics(currentQuery);
            
            if (messageTopics.length === 0 || queryTopics.length === 0) return 0;
            
            // Calculate weighted topic overlap
            let relevanceScore = 0;
            queryTopics.forEach(topic => {
                if (messageTopics.includes(topic)) {
                    relevanceScore += contextExtractors[topic].weight || 1.0;
                }
            });
            
            return relevanceScore / queryTopics.length;
        })();

        // Content similarity: check for similar words/phrases
        const contentRelevance = (() => {
            const msgWords = new Set(message.data.text.toLowerCase().split(/\W+/));
            const queryWords = new Set(currentQuery.toLowerCase().split(/\W+/));
            const intersection = new Set([...msgWords].filter(x => queryWords.has(x)));
            return intersection.size / Math.max(msgWords.size, queryWords.size);
        })();

        const relevance = (timeRelevance * 0.3) + (topicRelevance * 0.5) + (contentRelevance * 0.2);
        console.log('Calculated relevance:', {
            message: message.data.text,
            timeRelevance,
            topicRelevance,
            contentRelevance,
            finalRelevance: relevance
        });

        return relevance;
    }

    function getRelevantContext(currentQuery) {
        try {
            if (!currentQuery || typeof currentQuery !== 'string') {
                console.warn('Invalid query provided to getRelevantContext:', currentQuery);
                return getEmptyContext();
            }

            // Get chat history with validation
            let history = [];
            try {
                const savedHistory = localStorage.getItem(`chat_${sessionId}`);
                history = savedHistory ? JSON.parse(savedHistory) : [];
                if (!Array.isArray(history)) {
                    console.warn('Invalid history format, resetting to empty array');
                    history = [];
                }
            } catch (historyError) {
                console.error('Error loading chat history:', historyError);
                history = [];
            }
            
            // Score and sort messages by relevance with validation
            const scoredMessages = history
                .filter(msg => msg && msg.data && msg.data.text)
                .map(msg => {
                    try {
                        const relevance = calculateMessageRelevance(msg, currentQuery);
                        return { ...msg, relevance };
                    } catch (relevanceError) {
                        console.error('Error calculating message relevance:', relevanceError);
                        return { ...msg, relevance: 0 };
                    }
                })
                .filter(msg => msg.relevance > 0.4)
                .sort((a, b) => b.relevance - a.relevance)
                .slice(0, 10);  // Update to keep 10 most relevant messages

            // Get persistent context with validation
            let persistentContext = {};
            try {
                persistentContext = getRelevantPersistentContext(currentQuery);
            } catch (persistentError) {
                console.error('Error getting persistent context:', persistentError);
            }

            // Extract user context with validation
            let userContext = {};
            try {
                userContext = extractUserContext(scoredMessages);
            } catch (extractError) {
                console.error('Error extracting user context:', extractError);
            }

            // Merge contexts with validation
            let mergedContext = {};
            try {
                mergedContext = mergeContexts(persistentContext, userContext);
            } catch (mergeError) {
                console.error('Error merging contexts:', mergeError);
                mergedContext = { ...persistentContext, ...userContext };
            }

            // Normalize context for the model with validation
            const normalizedContext = {};
            Object.entries(mergedContext).forEach(([category, fields]) => {
                if (!fields || typeof fields !== 'object') return;
                
                normalizedContext[category] = {};
                Object.entries(fields).forEach(([field, data]) => {
                    try {
                        if (!data) return;
                        
                        if (data.normalized) {
                            normalizedContext[category][field] = data.normalized;
                        } 
                        else if (data.type || data.unit || data.number) {
                            normalizedContext[category][field] = {
                                type: data.type || null,
                                unit: data.unit || null,
                                number: typeof data.number === 'number' ? data.number : null,
                                value: data.value || null
                            };
                        }
                        else {
                            normalizedContext[category][field] = data.value || data;
                        }
                    } catch (fieldError) {
                        console.error(`Error normalizing field ${category}.${field}:`, fieldError);
                    }
                });
                
                if (Object.keys(normalizedContext[category]).length === 0) {
                    delete normalizedContext[category];
                }
            });

            // Add metadata with validation
            const contextMetadata = {
                context_version: CONTEXT_VERSION,
                last_updated: new Date().toISOString(),
                categories: Object.keys(normalizedContext),
                confidence_scores: Object.entries(mergedContext).reduce((acc, [category, fields]) => {
                    if (fields && typeof fields === 'object') {
                        acc[category] = Object.entries(fields).reduce((fieldAcc, [field, data]) => {
                            if (data && typeof data === 'object') {
                                fieldAcc[field] = typeof data.confidence === 'number' ? 
                                    Math.max(0, Math.min(1, data.confidence)) : 0.5;
                            }
                            return fieldAcc;
                        }, {});
                    }
                    return acc;
                }, {})
            };

            const context = {
                conversation_history: scoredMessages.map(msg => ({
                    role: msg.type === 'user' ? 'user' : 'assistant',
                    content: msg.data.text || '',
                    timestamp: msg.timestamp || new Date().toISOString(),
                    relevance: typeof msg.relevance === 'number' ? msg.relevance : 0.5
                })),
                user_context: normalizedContext,
                context_metadata: contextMetadata
            };

            // Update persistent context with validation
            try {
                Object.entries(userContext).forEach(([category, fields]) => {
                    Object.entries(fields).forEach(([field, value]) => {
                        if (value) {
                            const confidence = calculateConfidence(value, currentQuery, category, field);
                            updatePersistentContext(category, field, value, confidence);
                        }
                    });
                });
            } catch (updateError) {
                console.error('Error updating persistent context:', updateError);
            }

            // Clean up old context periodically
            try {
                if (history.length % 10 === 0) {
                    cleanupPersistentContext();
                }
            } catch (cleanupError) {
                console.error('Error cleaning up persistent context:', cleanupError);
            }

            if (DEBUG_MODE) {
                console.group('Final Context for Model');
                console.log('Normalized Context:', normalizedContext);
                console.log('Context Metadata:', contextMetadata);
                console.log('Full Context Object:', context);
                console.groupEnd();
            }

            return context;
        } catch (e) {
            console.error('Error in getRelevantContext:', e);
            return getEmptyContext();
        }
    }

    // Helper function for empty context
    function getEmptyContext() {
        return { 
            conversation_history: [], 
            user_context: {},
            context_metadata: {
                context_version: CONTEXT_VERSION,
                last_updated: new Date().toISOString(),
                categories: [],
                confidence_scores: {}
            }
        };
    }

    // Helper function to merge contexts
    function mergeContexts(persistentContext, currentContext) {
        const merged = { ...persistentContext };
        
        Object.entries(currentContext).forEach(([category, fields]) => {
            if (!merged[category]) {
                merged[category] = {};
            }
            
            Object.entries(fields).forEach(([field, value]) => {
                // If the field exists in both, use the one with higher confidence or more recent
                if (merged[category][field]) {
                    const persistentData = merged[category][field];
                    const persistentTime = new Date(persistentData.timestamp).getTime();
                    const currentTime = new Date().getTime();
                    
                    // Use current context if it's newer or has higher confidence
                    if (currentTime > persistentTime || 
                        (currentContext[category]?.confidence || 0.5) > (persistentData.confidence || 0.5)) {
                        merged[category][field] = {
                            value: value,
                            timestamp: new Date().toISOString(),
                            confidence: currentContext[category]?.confidence || 0.5
                        };
                    }
                } else {
                    // Add new field from current context
                    merged[category][field] = {
                        value: value,
                        timestamp: new Date().toISOString(),
                        confidence: currentContext[category]?.confidence || 0.5
                    };
                }
            });
        });
        
        return merged;
    }

    function extractUserContext(messages) {
        const context = {};
        
        messages.forEach(msg => {
            if (msg.type === 'user' && msg.data && msg.data.text) {
                const text = msg.data.text.toLowerCase();
                
                Object.entries(contextExtractors).forEach(([category, config]) => {
                    Object.entries(config.patterns).forEach(([subType, patterns]) => {
                        if (Array.isArray(patterns)) {
                            if (!context[category]) {
                                context[category] = {};
                            }
                            if (!context[category][subType]) {
                                context[category][subType] = [];
                            }
                            
                            patterns.forEach(pattern => {
                                if (typeof pattern === 'object' && pattern.pattern) {
                                    // Handle structured patterns with extractors
                                    const match = text.match(pattern.pattern);
                                    if (match) {
                                        const extracted = pattern.extract(match);
                                        context[category][subType].push({
                                            ...extracted,
                                            timestamp: msg.timestamp,
                                            confidence: calculateConfidence(match[0], text, category, subType)
                                        });
                                        console.log(`Extracted ${category}.${subType}:`, extracted);
                                    }
                                } else {
                                    // Handle simple regex patterns
                                    const match = text.match(pattern);
                                    if (match) {
                                        context[category][subType].push({
                                            value: match[0],
                                            timestamp: msg.timestamp,
                                            confidence: calculateConfidence(match[0], text, category, subType)
                                        });
                                        console.log(`Extracted ${category}.${subType}:`, match[0]);
                                    }
                                }
                            });
                        }
                    });
                });
            }
        });

        const processedContext = processExtractedContext(context);
        console.log('Processed context:', processedContext);
        return processedContext;
    }

    function calculateConfidence(match, fullText, category = null, subType = null) {
        let confidence = 0.5; // Base confidence
        
        // Get category-specific confidence modifiers
        const modifiers = category && contextExtractors[category]?.confidence_modifiers || {
            explicit_statement: 0.2,
            contextual_mention: -0.1,
            multiple_mentions: 0.15,
            uncertainty: -0.2,
            temporal_markers: 0.1
        };
        
        // Check for explicit statements
        if (/\b(is|are|has|have|does|do)\b/i.test(fullText)) {
            confidence += modifiers.explicit_statement;
        }
        
        // Check for uncertainty
        if (/\b(maybe|think|guess|probably|might|could|not sure|possibly|perhaps)\b/i.test(fullText)) {
            confidence += modifiers.uncertainty;
        }
        
        // Check for temporal markers
        if (/\b(now|currently|presently|at the moment|these days|lately|today)\b/i.test(fullText)) {
            confidence += modifiers.temporal_markers;
        }
        
        // Check for multiple mentions
        const matchCount = (fullText.match(new RegExp(match, 'gi')) || []).length;
        if (matchCount > 1) {
            confidence += modifiers.multiple_mentions;
        }
        
        // Adjust based on match position (earlier mentions might be more relevant)
        const matchPosition = fullText.toLowerCase().indexOf(match.toLowerCase());
        if (matchPosition !== -1) {
            const positionScore = 1 - (matchPosition / fullText.length);
            confidence += positionScore * 0.1;
        }
        
        // Adjust based on surrounding context
        const surroundingWords = fullText.split(/\W+/).length;
        const contextRichness = Math.min(surroundingWords / 10, 1); // Cap at 1
        confidence += contextRichness * 0.1;
        
        // Category-specific adjustments
        if (category && subType) {
            switch(category) {
                case 'demographics':
                    // Higher confidence for direct age statements
                    if (subType === 'baby_age' && /\b(is|turned)\b.*old/i.test(fullText)) {
                        confidence += 0.2;
                    }
                    break;
                    
                case 'feeding':
                    // Higher confidence for current feeding patterns
                    if (subType === 'feeding_type' && /\b(currently|now)\b/i.test(fullText)) {
                        confidence += 0.15;
                    }
                    break;
                    
                case 'sleep':
                    // Higher confidence for recent sleep patterns
                    if (/\b(last night|recently|past few)\b/i.test(fullText)) {
                        confidence += 0.15;
                    }
                    break;
            }
        }
        
        // Log confidence calculation if in debug mode
        if (DEBUG_MODE) {
            console.log('Confidence calculation:', {
                match,
                category,
                subType,
                baseConfidence: 0.5,
                finalConfidence: Math.max(0, Math.min(1, confidence)),
                adjustments: {
                    explicitStatement: /\b(is|are|has|have|does|do)\b/i.test(fullText),
                    uncertainty: /\b(maybe|think|guess|probably|might|could|not sure)\b/i.test(fullText),
                    temporalMarkers: /\b(now|currently|presently)\b/i.test(fullText),
                    multipleMatches: matchCount > 1,
                    positionScore: matchPosition !== -1 ? 1 - (matchPosition / fullText.length) : 0,
                    contextRichness: contextRichness
                }
            });
        }
        
        return Math.max(0, Math.min(1, confidence));
    }

    function processExtractedContext(rawContext) {
        const processed = {};
        
        Object.entries(rawContext).forEach(([category, subTypes]) => {
            processed[category] = {};
            
            Object.entries(subTypes).forEach(([subType, matches]) => {
                if (!Array.isArray(matches) || matches.length === 0) {
                    return;
                }
                
                // Sort by confidence and recency
                const sorted = [...matches].sort((a, b) => {
                    const timeWeight = 0.3;
                    const confidenceWeight = 0.7;
                    
                    const timeA = new Date(a.timestamp).getTime();
                    const timeB = new Date(b.timestamp).getTime();
                    const timeDiff = (timeB - timeA) / (1000 * 60 * 60); // hours
                    const timeScore = Math.max(0, 1 - (timeDiff / 24)); // Decay over 24 hours
                    
                    const scoreA = (a.confidence * confidenceWeight) + (timeScore * timeWeight);
                    const scoreB = (b.confidence * confidenceWeight) + (timeScore * timeWeight);
                    
                    return scoreB - scoreA;
                });
                
                // Take the highest confidence match
                if (sorted.length > 0) {
                    const bestMatch = sorted[0];
                    processed[category][subType] = bestMatch.normalized || bestMatch.value;
                }
            });
            
            // Remove empty sub-categories
            if (Object.keys(processed[category]).length === 0) {
                delete processed[category];
            }
        });
        
        if (DEBUG_MODE) {
            console.log('Raw context:', rawContext);
            console.log('Processed context:', processed);
        }
        
        return processed;
    }

    // Initialize or get existing session ID
    let sessionId = localStorage.getItem('sessionId');
    if (!sessionId) {
        sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('sessionId', sessionId);
    }

    // Handle disclaimer visibility
    function handleDisclaimer() {
        const hasAcceptedDisclaimer = sessionStorage.getItem(`disclaimer_${sessionId}`);
        const disclaimerModal = document.getElementById('disclaimerModal');
        
        if (!hasAcceptedDisclaimer) {
            disclaimerModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        } else {
            disclaimerModal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    // Handle disclaimer acceptance
    function acceptDisclaimer() {
        const disclaimerModal = document.getElementById('disclaimerModal');
        sessionStorage.setItem(`disclaimer_${sessionId}`, 'true');
        disclaimerModal.style.display = 'none';
        document.body.style.overflow = '';
    }

    // Event listener for the agree button
    if (agreeButton) {
        agreeButton.addEventListener('click', function(e) {
            e.preventDefault();
            acceptDisclaimer();
        });
    }

    // Clear any existing session data on new chat
    if (window.location.href.includes('?new')) {
        sessionStorage.clear();
    }

    // Initialize disclaimer on page load
    handleDisclaimer();

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
            
            // Ensure data has the correct structure
            const messageToSave = {
                data: typeof data === 'string' ? { text: data } : data,
                type,
                timestamp: new Date().toISOString()
            };
            
            messages.push(messageToSave);
            localStorage.setItem(`chat_${sessionId}`, JSON.stringify(messages));
            console.log('Saved message to history:', messageToSave);
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

        // Don't clear persistent context, but clean it up
        cleanupPersistentContext();

        if (DEBUG_MODE) {
            const persistentContext = initializePersistentContext();
            console.log('Persistent context after new chat:', persistentContext);
        }
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

    // Add Debug Functions
    function debugContext(context, query) {
        if (!DEBUG_MODE) return;
        
        console.group('Context Debug Info');
        console.log('Current Query:', query);
        console.log('Relevant History:', context.conversation_history);
        console.log('User Context:', context.user_context);
        
        // Log topic analysis
        const queryTopics = identifyTopics(query);
        console.log('Detected Topics:', queryTopics);
        
        // Log relevance scores
        if (context.conversation_history.length > 0) {
            console.log('Message Relevance Scores:');
            context.conversation_history.forEach(msg => {
                console.log(`${msg.content.substring(0, 30)}... : ${calculateMessageRelevance({
                    data: { text: msg.content },
                    timestamp: msg.timestamp
                }, query)}`);
            });
        }
        console.groupEnd();
    }

    // Modify the chat form submission to include debug info
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
            let beforeContext;  // Define beforeContext in the proper scope
            
            // Debug: Log persistent context before processing
            if (DEBUG_MODE) {
                console.group('Persistent Context Debug');
                beforeContext = initializePersistentContext();
                console.log('Persistent Context Before Processing:', beforeContext);
            }

            // Get relevant context for the current query
            const context = getRelevantContext(message);
            
            // Add debug information
            debugContext(context, message);

            // Debug: Log persistent context after processing
            if (DEBUG_MODE) {
                const afterContext = initializePersistentContext();
                console.log('Persistent Context After Processing:', afterContext);
                console.log('Context Changes:', {
                    added: beforeContext ? Object.keys(afterContext).filter(k => !beforeContext[k]) : [],
                    modified: beforeContext ? Object.keys(afterContext).filter(k => 
                        beforeContext[k] && JSON.stringify(beforeContext[k]) !== JSON.stringify(afterContext[k])
                    ) : []
                });
                console.groupEnd();
            }

            const persistentContext = initializePersistentContext();
            const normalizedPersistentContext = Object.entries(persistentContext).reduce((acc, [category, data]) => {
                if (category === 'version' || category === 'lastUpdated' || category === 'relevanceScores') return acc;
                if (typeof data === 'object') {
                    acc[category] = Object.entries(data).reduce((fieldAcc, [field, value]) => {
                        if (value && typeof value === 'object') {
                            fieldAcc[field] = value.normalized || value.value || value;
                        }
                        return fieldAcc;
                    }, {});
                }
                return acc;
            }, {});

            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    session_id: sessionId,
                    language: detectedLanguage,
                    context: {
                        conversation_history: context.conversation_history,
                        user_context: context.user_context,
                        context_metadata: context.context_metadata,
                        persistent_context: normalizedPersistentContext
                    }
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
}); 