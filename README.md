# Babywise - AI-Powered Parenting Assistant

Babywise is an intelligent chatbot system designed to provide personalized parenting advice and recommendations. The system uses a multi-agent architecture to handle various aspects of parenting queries, from baby gear recommendations to sleep training advice.

## Features

- 🤖 Multi-agent architecture for specialized advice
- 💬 Context-aware conversation management
- 🎯 Dynamic field detection and validation
- 📝 Structured response formatting
- 🔄 Persistent context maintenance

## Project Structure

```
babywise/
├── src/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── baby_gear_agent.py
│   │   └── activity_agent.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── chat_session.py
│   │   └── agent_factory.py
│   ├── models/
│   │   └── chat.py
│   ├── routes/
│   │   └── chat.py
│   ├── database/
│   │   └── db_manager.py
│   ├── middleware/
│   │   └── debug.py
│   └── static/
│       └── script.js
├── tests/
├── docs/
└── config/
```

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/babywise.git
cd babywise
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.template .env
# Edit .env with your API keys and configuration
```

5. Run the application:
```bash
python src/server.py
```

## Architecture

### Agent System
- Each agent specializes in specific parenting topics
- Dynamic agent selection based on query content
- Maintains context throughout conversations

### Context Management
- Persistent storage of conversation state
- Dynamic field detection and validation
- Context-aware response generation

### Response Generation
- Structured format based on query type
- Validation of context maintenance
- Dynamic follow-up question generation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT models
- Contributors and maintainers
- The parenting community for inspiration and feedback 