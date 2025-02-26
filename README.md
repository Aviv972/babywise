# Babywise Assistant

A WhatsApp-like chatbot interface for baby care advice, powered by LangChain and LangGraph.

## Features

- Multi-language support (English, Spanish, French, German, Hebrew, Arabic)
- Context retention between messages
- Domain-specific advice (sleep, feeding, development, baby gear)
- WhatsApp-like UI for familiar user experience

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/babywise.git
cd babywise
```

2. Create a virtual environment:
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
# Create a .env file with your API keys
echo "OPENAI_API_KEY=your_openai_api_key" > .env
```

## Running the Application

Start the server using the provided script:

```bash
./start_server.sh
```

Or manually:

```bash
python -m src.simplified_server
```

Then open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. Type your baby care question in the chat input
2. The assistant will automatically detect your language
3. Receive personalized advice based on your specific context
4. Start a new conversation by clicking the "New Chat" button

## Project Structure

- `src/`: Source code
  - `langchain/`: LangChain and LangGraph workflow
  - `static/`: Frontend files (HTML, CSS, JavaScript)
  - `simplified_server.py`: FastAPI server

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 