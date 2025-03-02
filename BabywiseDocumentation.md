# Babywise Chatbot Documentation

## 1. Introduction
The Babywise Chatbot is a domain-specific assistant designed to provide personalized baby care guidance to new and future parents. The chatbot leverages dynamic prompt templates, context management, and memory persistence using LangChain and LangGraph. In addition, a Baby Routine Tracker feature allows parents to log feeding and sleeping events, with the aggregated data used to generate summary reports.

## 2. Project Overview
### Purpose
- **Personalized Advice**: Provide tailored advice on baby care topics such as sleep, feeding, baby gear, child development, and health/safety.
- **Dynamic Interaction**: Use clarifying questions to gather necessary details only when required.
- **Routine Tracking**: Enable parents to log routine events to monitor their baby's schedule over daily, weekly, or monthly periods.

### Key Concepts
- **Unified Agent & Domain-Specific Prompts**: A single chatbot agent processes all queries but dynamically adapts its responses based on the detected domain (e.g., sleep, feeding).
- **Context Management via LangChain/LangGraph**: Conversation history is maintained and persisted, ensuring that the chatbot's responses are context-aware.
- **Memory Persistence**: Using LangGraph's in-memory (or alternative) persistence to support multi-turn conversations and multiple conversation threads.

## 3. Architecture Overview
### Backend
The backend is built on Python using LangChain and LangGraph. The main components include:

#### State Schema (BabywiseState):
Defines the conversation state, including:

- messages: List of chat messages (using classes like HumanMessage, AIMessage).
- context: Extracted data (e.g., baby age, name, budget, health conditions).
- domain: The current topic domain (e.g., sleep, feeding).
- metadata: Additional state information such as timestamps.
- language: Current conversation language.

#### Workflow Nodes:
The system is organized as a series of nodes in a workflow:

- **Extract Context**: Scans the conversation history to extract relevant details using regex patterns (e.g., baby age, name, budget).
- **Select Domain**: Uses keyword matching to decide which domain-specific prompt to use.
- **Generate Response**: Builds the prompt with domain-specific instructions (including language and gender-specific guidelines for Hebrew) and calls the LLM (via ChatOpenAI) to generate a response.
- **Post-Process**: Adds metadata (e.g., timestamps) and logs the state summary.

#### Global State & Thread Management:
A global memory saver and a thread state cache support multi-user conversations by storing and retrieving the state for each thread (using a unique thread_id).

#### Integration with LangGraph:
The workflow is compiled into a LangGraph application that persists the message history, allowing for multi-turn conversations and state continuity across sessions.

### Frontend
The user interface is built using HTML, CSS, and JavaScript. Key elements include:

#### HTML Structure:
A single-page layout that includes:

- A header with the Babywise Assistant title, avatar, and a "New Chat" button.
- A message container where conversation messages are dynamically rendered.
- An input area where users can type their messages and send them.

#### CSS Styling:
The design mimics a modern chat interface with:

- Distinct styling for user and assistant messages.
- Responsive design adjustments for mobile devices.
- A "typing indicator" to enhance user experience during response generation.

#### JavaScript Integration:
(Referenced via /static/script.js) handles the chat message submission, updates the message view in real time, and manages the interaction with the backend service.

## 4. Setup and Installation
### Dependencies
#### Python Libraries:
- langchain-core, langgraph, langchain_openai
- Additional utility libraries (e.g., re, json, logging, datetime)

#### Frontend Libraries:
- Google Fonts (Open Sans)
- Font Awesome for icons

### Installation Steps
#### Backend Setup:
Install the required packages:

```bash
pip install langchain-core langgraph langchain_openai
```

Set up environment variables for API keys (e.g., LANGSMITH_API_KEY, OPENAI_API_KEY).

#### Frontend Setup:
Ensure the HTML file and associated CSS/JS files are served correctly (e.g., via a web server or integrated into a web framework).

#### Running the Chatbot:
Use the provided Python functions (such as chat(message, thread_id, language)) to process incoming messages. The global workflow handles state retrieval, processing, and response generation.

## 5. Detailed Code Structure
### Workflow Functions
#### extract_context(state: BabywiseState)
Parses recent messages to extract context like baby age, name, gender, budget, and health conditions using regex patterns.

#### select_domain(state: BabywiseState)
Evaluates the latest message against pre-defined keywords for each domain (sleep, feeding, baby gear, etc.) and sets the most relevant domain.

#### generate_response(state: BabywiseState)
Creates a dynamic prompt by combining:

- A domain-specific prompt from DOMAIN_PROMPTS.
- Language and gender-specific instructions (particularly for Hebrew).
- Additional context instructions if critical information is missing.

Then, it calls the LLM with the constructed prompt and appends the response to the conversation history.

#### post_process(state: BabywiseState)
Adds metadata such as timestamps and logs the final state.

### Workflow Compilation
- The workflow is defined as a sequence of nodes (extract → select → generate → post-process) and compiled with a memory saver (via MemorySaver).
- Global state management and helper functions (e.g., get_default_state, add_user_message) ensure smooth multi-turn conversations.

### Chat Functionality
#### chat(message: str, thread_id: str, language: str = "en")
This asynchronous function is the main entry point:
- It checks for an existing conversation state (from cache or persistent memory).
- It adds the new user message.
- It runs the workflow to generate a new assistant response.
- It returns the response text along with context and metadata.

## 6. Frontend Overview
### Frontend & WhatsApp-like Chat UI
The Babywise Assistant's frontend is designed to deliver a user experience very similar to WhatsApp's chat interface. This approach ensures that users feel at home while interacting with the chatbot. Here's an overview of the design and implementation:

#### Visual Design & Layout
##### WhatsApp-inspired Color Scheme and Elements:
The CSS defines a set of custom properties (variables) to mimic WhatsApp's look and feel. For example:

###### Backgrounds:
- The overall page uses a clean white background (--page-bg-color: #FFFFFF).
- The chat container uses a WhatsApp-style background (--whatsapp-bg: #E5DDD5).

###### Message Bubbles:
- User messages appear in a greenish bubble (--user-bubble: #DCF8C6), while bot responses use a white bubble (--bot-bubble: #FFFFFF).

###### Header and Input Styling:
- The header features a bold, contrasting background (--header-bg: #3D8C6F) with white text, ensuring clear visibility.
- The input area is styled to resemble WhatsApp's input box, complete with a subtle border (--input-border: #D0D0D0) and send button matching the header color.

##### Responsive and Adaptive Design:
Media queries ensure that the chat interface scales smoothly on mobile devices:

- On smaller screens, the chat container takes up the full viewport height and width.
- The layout adjusts padding and element sizing to maintain readability and usability.

##### Message Grouping & Timestamps:
- Messages sent in rapid succession are intelligently grouped to reduce clutter, with only the first message in a group showing a timestamp.
- The timestamp styling (--timestamp: #999999) is subtle and consistent with WhatsApp's design.

##### RTL Support:
- The CSS includes classes for right-to-left text, ensuring that languages such as Hebrew or Arabic are displayed correctly and naturally, with flipped bubble alignment and adjusted clip-paths for speech bubble "tails."

#### Interactive Components
##### Header & New Chat Functionality:
- The header not only displays the assistant's avatar and status (online) but also provides a "New Chat" button.
- The button, when clicked, prompts the user for confirmation before starting a new session, preserving chat history in localStorage.

##### Chat Messages Area:
- The main message area is scrollable and designed to mimic the conversation flow of WhatsApp.
- A typing indicator with animated dots provides visual feedback while the assistant is generating a response.

##### Input Area:
- The message input field dynamically adjusts its text alignment based on language (e.g., RTL for Hebrew) and enables/disables the send button based on content.
- The send button is styled to change color on hover, offering clear interactive cues.

#### Persistent and Contextual Features
##### LocalStorage Integration for Session Continuity:
- The app stores a unique session ID in localStorage to maintain conversation continuity across page reloads.
- Chat history is also saved and loaded on startup, ensuring users can review past interactions.

##### Context Management and Debugging:
- The JavaScript includes a robust persistent context management system. This system extracts and stores relevant conversation context, using versioning and confidence scores to help improve future responses.
- Debug mode is available for developers to log context changes and message relevance, ensuring that context extraction works as intended.

##### Command and Context Handling:
- In addition to standard chat functionality, the frontend supports command parsing for routine tracking. Commands like "sleep 8:30pm" or "summary today" are detected and processed appropriately, integrating seamlessly with the backend's routine tracker.
- The system also provides debug information and context feedback, helping to ensure that the right details are passed along with each message.

## 7. Routine Tracker Implementation
The Babywise Chatbot not only offers conversational advice but also includes a Baby Routine Tracker to help parents log and monitor key routine events (such as sleep and feeding). The implementation is planned in four phases:

### Database & Backend Setup
#### Create Event Database Schema:
- Define an SQLite table for routine events with columns: id, thread_id, event_type, start_time, end_time, and notes.
- Provide a database initialization script.

#### Implement Database Access Layer:
- Create functions for CRUD operations on routine events.
- Implement query functions to retrieve events by a specific date range.

#### Add API Endpoints to FastAPI Server:
- Create an /events endpoint to create and retrieve routine events.
- Create a /summary endpoint to generate daily, weekly, or monthly summary reports.

#### Implement Command Parser:
- Develop a function that detects command patterns in user messages.
- Extract event type and time information from commands supporting various formats, for example:

##### Sleep Tracking:
- Start: sleep [time], bed [time], nap [time]
- End: woke [time], wake [time], awake [time]

##### Feeding Tracking:
- Start: feed [time], feeding [time], fed [time]
- End: done feeding [time], finished feeding [time]

##### Summary Requests:
- summary today, summary week, summary month

##### Help Command:
- help tracking

##### Time Formats Supported:
- Both 12-hour (e.g., 8:30pm, 8:30 PM) and 24-hour (e.g., 20:30) formats.
- Allow shorthand times like 8pm or 14:30.
- Default to the current day when only a time is provided, using the browser's timezone. 