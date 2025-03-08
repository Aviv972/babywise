# Manual End-to-End Test Plan: Baby Tracker & Chat Query Interaction

## Objective
This test plan verifies that the Baby Wise system correctly handles two primary types of user interactions:
1. Queries about baby development or baby products (like strollers)
2. Commands to track baby routine events (like sleep)

## Prerequisites
- The Baby Wise application is running and accessible
- Tester has access to a web browser or mobile device
- Internet connection is available

## Test Environment
- Web browser: Chrome, Firefox, Safari, or Edge (latest versions)
- Mobile devices: iOS and Android (optional)
- Server environment: Production or Staging

## Test Case 1: Query About Baby Development

### Description
Verify that the system correctly processes and responds to queries about baby development.

### Steps
1. Open the Baby Wise application
2. Ensure you are in the chat interface
3. Type and send the following query: "At what age can I introduce solid foods to my baby?"
4. Wait for the system to process and respond

### Expected Results
- The system should respond within 5 seconds
- The response should contain relevant information about introducing solid foods to babies
- The response should mention appropriate age ranges (typically around 4-6 months)
- The response should be well-structured and easy to read
- The response may include safety considerations and recommendations
- No error messages should appear

### Pass/Fail Criteria
- PASS: The system provides a relevant, accurate response about introducing solid foods
- FAIL: The system fails to respond, provides irrelevant information, or treats the query as a tracking command

## Test Case 2: Query About Baby Strollers

### Description
Verify that the system correctly processes and responds to queries about baby products.

### Steps
1. Open the Baby Wise application
2. Ensure you are in the chat interface
3. Type and send the following query: "What features should I look for in a baby stroller?"
4. Wait for the system to process and respond

### Expected Results
- The system should respond within 5 seconds
- The response should contain relevant information about baby stroller features
- The response should mention important considerations like safety features, maneuverability, storage, etc.
- The response should be well-structured and easy to read
- No error messages should appear

### Pass/Fail Criteria
- PASS: The system provides a relevant, informative response about baby stroller features
- FAIL: The system fails to respond, provides irrelevant information, or treats the query as a tracking command

## Test Case 3: Save Sleep Event in Baby Tracker

### Description
Verify that the system correctly processes commands to track baby sleep events.

### Steps
1. Open the Baby Wise application
2. Ensure you are in the chat interface
3. Note the current time for verification purposes
4. Type and send the following command: "My baby just fell asleep"
5. Wait for the system to process and respond
6. Navigate to the tracking history or summary view (if available)

### Expected Results
- The system should respond within 5 seconds
- The response should confirm that a sleep event has been logged
- The response should include the timestamp of the logged event (close to the current time)
- If navigating to the tracking history, the new sleep event should appear in the list
- The event should be correctly categorized as a "sleep" event
- No error messages should appear

### Pass/Fail Criteria
- PASS: The system correctly identifies the command as a sleep event and logs it with the appropriate timestamp
- FAIL: The system fails to recognize the command, doesn't log the event, or treats it as a general query

## Test Case 4: Offline Mode Sleep Event Tracking

### Description
Verify that the system correctly handles sleep event tracking when offline.

### Steps
1. Open the Baby Wise application
2. Disconnect from the internet (turn on airplane mode or disable Wi-Fi/cellular data)
3. Ensure you are in the chat interface
4. Type and send the following command: "My baby just fell asleep"
5. Wait for the system to process and respond
6. Reconnect to the internet
7. Wait for automatic synchronization or manually trigger sync
8. Navigate to the tracking history or summary view (if available)

### Expected Results
- The system should indicate that the device is offline
- The system should confirm that the event has been saved locally
- After reconnecting, the system should synchronize the local data with the server
- The event should appear in the tracking history after synchronization
- No data should be lost during the offline-online transition

### Pass/Fail Criteria
- PASS: The system saves the event locally when offline and successfully syncs it when back online
- FAIL: The system loses the event data, fails to sync, or doesn't provide appropriate offline notifications

## Test Case 5: Multiple Consecutive Commands

### Description
Verify that the system correctly handles multiple consecutive tracking commands.

### Steps
1. Open the Baby Wise application
2. Ensure you are in the chat interface
3. Send the following command: "My baby fell asleep at 2:30pm"
4. Wait for the system to process and respond
5. Send another command: "Baby woke up at 4:15pm"
6. Wait for the system to process and respond
7. Send a third command: "Started feeding at 4:30pm"
8. Wait for the system to process and respond
9. Navigate to the tracking history or summary view (if available)

### Expected Results
- The system should process each command correctly
- Each response should confirm the specific event type that was logged
- All three events should appear in the tracking history
- The events should have the correct timestamps as specified in the commands
- The sleep duration should be calculated correctly (approximately 1 hour 45 minutes)
- No error messages should appear

### Pass/Fail Criteria
- PASS: The system correctly processes all three commands and logs the events with the specified timestamps
- FAIL: The system fails to process any of the commands correctly or logs incorrect information

## Test Case 6: Request Summary After Tracking Events

### Description
Verify that the system correctly generates a summary of tracked events.

### Steps
1. Open the Baby Wise application
2. Ensure you are in the chat interface
3. Send at least 2-3 tracking commands (mix of sleep and feeding events)
4. Wait for the system to process and respond to each command
5. Send the following command: "Show me today's summary"
6. Wait for the system to process and respond

### Expected Results
- The system should respond with a summary of the day's events
- The summary should include all events that were previously logged
- The summary should be well-organized by event type
- For sleep events, the summary should include duration information
- The summary should be formatted in a readable way
- No error messages should appear

### Pass/Fail Criteria
- PASS: The system generates a comprehensive, accurate summary of all tracked events
- FAIL: The system fails to generate a summary, omits events, or presents the information in a confusing manner

## Notes for Testers
- Document any unexpected behavior or error messages
- Note the response times for each interaction
- Take screenshots of any issues encountered
- Test with different phrasings of the same commands to verify robustness
- If possible, test in different languages to verify internationalization support 