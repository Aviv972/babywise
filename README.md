# Babywise Assistant

<<<<<<< HEAD
A comprehensive assistant for baby care advice and routine tracking, with full Hebrew language support.

## Features

### Chat Interface
- Natural language conversation about baby care topics
- Personalized advice based on baby's age, gender, and other context
- Multilingual support with full Hebrew language support (RTL formatting)
- Domain-specific responses for sleep, feeding, development, health, and baby gear
- WhatsApp-like chat interface

### Routine Tracker
- Track sleep and feeding events using natural language commands
- View daily, weekly, and monthly summaries
- Record start and end times for events
- Add notes to events
- Support for Hebrew commands

## Project Structure

```
├── api/
│   ├── index.py                # Vercel entry point
│   └── requirements.txt        # Vercel dependencies
├── backend/
│   ├── api/
│   │   ├── main.py              # Main API endpoints
│   │   └── routine_endpoints.py # Routine tracker API endpoints
│   ├── db/
│   │   └── routine_tracker.py   # Database operations for routine tracking
│   ├── state_schema.py          # State schema for the chatbot
│   └── workflow/
│       ├── command_parser.py    # Parser for routine tracking commands
│       ├── domain_prompts.py    # Domain-specific prompts
│       ├── extract_context.py   # Context extraction from messages
│       ├── generate_response.py # Response generation
│       ├── post_process.py      # Post-processing of responses
│       ├── select_domain.py     # Domain selection based on context
│       └── workflow.py          # Main workflow orchestration
├── frontend/
│   ├── baby-icon.svg            # Baby icon for the UI
│   ├── favicon.svg              # Favicon for the browser tab
│   ├── index.html               # Main HTML file
│   ├── script.js                # JavaScript for the chat interface
│   └── style.css                # CSS styling
├── server.py                    # Server to connect frontend and backend
└── vercel.json                  # Vercel deployment configuration
```

## Getting Started

### Prerequisites
- Python 3.9+
- FastAPI
- LangChain
- LangGraph
- SQLite

### Local Development

1. Clone the repository
```bash
git clone https://github.com/yourusername/babywise-assistant.git
cd babywise-assistant
```

2. Install dependencies
=======
A smart AI assistant for parents, providing personalized advice and product recommendations for baby care.

## Features

- Personalized baby care advice
- Product recommendations with real-time pricing
- Context-aware conversations
- Multi-agent architecture for specialized responses
- Support for both English and Hebrew

## Tech Stack

- FastAPI
- OpenAI GPT-4
- Perplexity AI (Llama 3 models)
- SQLite
- Vercel for deployment

## Environment Variables

Create a `.env` file with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
MODEL_NAME=gpt-4o-mini
DATABASE_URL=sqlite:///chatbot.db
```

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/Aviv972/babywise.git
cd babywise
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
>>>>>>> 64a3e7edaee2f1f0d035ab9cce454790894bc3ab
```bash
pip install -r requirements.txt
```

<<<<<<< HEAD
3. Create a `.env` file with your OpenAI API key
```
OPENAI_API_KEY=your_api_key_here
```

4. Run the server
```bash
python server.py
```

5. Open your browser and navigate to `http://localhost:8000`

### Deployment on Vercel

This project is configured for deployment on Vercel:

1. Fork or clone this repository
2. Connect your GitHub repository to Vercel
3. Add your `OPENAI_API_KEY` as an environment variable in the Vercel project settings
4. Deploy!

## Usage

### Chat Interface
Simply type your baby care questions in the chat input and press Enter or click the send button.

### Routine Tracking Commands

#### Sleep Tracking (English)
- "Baby went to sleep at 8:30pm"
- "Put him to bed at 7pm"
- "She's napping at 2:30pm"
- "Baby woke up at 6am"
- "He's been awake since 5:30am"

#### Sleep Tracking (Hebrew)
- "התינוק נרדם ב-20:00"
- "שמתי אותו לישון ב-19:00"
- "היא ישנה מ-14:30"
- "התינוק התעורר ב-6:00"
- "הוא ער מ-5:30"

#### Feeding Tracking (English)
- "Started feeding at 9am"
- "Fed baby at 3pm"
- "Finished breastfeeding at 9:30am"
- "Done feeding at 4:15pm"

#### Feeding Tracking (Hebrew)
- "התחלתי להאכיל ב-9:00"
- "האכלתי את התינוק ב-15:00"
- "סיימתי הנקה ב-9:30"
- "סיימתי האכלה ב-16:15"

#### Summary Reports
- "Show me today's summary" / "הראה לי סיכום של היום"
- "Get weekly summary" / "קבל סיכום שבועי"
- "Summary for this month" / "סיכום לחודש הזה"

## API Endpoints

### Chat API
- `POST /api/chat` - Send a message to the chatbot
- `POST /api/reset/{thread_id}` - Reset a conversation thread
- `GET /api/context/{thread_id}` - Get the current context for a thread
- `GET /api/health` - Health check endpoint

### Routine Tracker API
- `POST /api/routine/events` - Create a new routine event
- `GET /api/routine/events` - Get events for a specific thread within a date range
- `PUT /api/routine/events/{event_id}` - Update an existing routine event
- `DELETE /api/routine/events/{event_id}` - Delete a routine event
- `GET /api/routine/summary/{thread_id}` - Generate a summary of routine events
- `GET /api/routine/latest/{thread_id}/{event_type}` - Get the most recent event of a specific type

## License
This project is licensed under the MIT License - see the LICENSE file for details. 
=======
4. Run the development server:
```bash
python src/server.py
```

The server will be available at `http://localhost:8004`

## Deployment to Vercel

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy:
```bash
vercel
```

4. Add environment variables in Vercel:
- Go to your project settings
- Add the environment variables from your `.env` file

## Project Structure

```
babywise/
├── src/
│   ├── agents/           # Specialized AI agents
│   ├── docs/            # Documentation and common questions
│   ├── services/        # Core services (LLM, Chat, etc.)
│   ├── database/        # Database management
│   ├── models/          # Data models
│   ├── static/          # Static files (HTML, CSS, JS)
│   └── server.py        # Main FastAPI application
├── tests/               # Test files
├── requirements.txt     # Python dependencies
├── vercel.json         # Vercel configuration
└── README.md           # This file
```

## API Endpoints

- `GET /`: Home page
- `POST /chat`: Chat endpoint
- `GET /health`: Health check
- `DELETE /session/{session_id}`: Clear chat session

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT models
- Contributors and maintainers
- The parenting community for inspiration and feedback 
>>>>>>> 64a3e7edaee2f1f0d035ab9cce454790894bc3ab
