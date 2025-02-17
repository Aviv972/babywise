# Babywise Assistant

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
```bash
pip install -r requirements.txt
```

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