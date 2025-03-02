# Babywise Assistant

A chatbot for baby care advice and routine tracking, built with FastAPI, LangChain, and OpenAI.

## Features

- **AI-Powered Baby Care Advice**: Get personalized advice on baby care topics
- **Routine Tracking**: Log and track your baby's sleep and feeding routines
- **Daily Summaries**: Generate summaries of your baby's day
- **Responsive UI**: Works on desktop and mobile devices

## Local Development

### Prerequisites

- Python 3.9+
- OpenAI API key

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd babywise-assistant
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Run the application:
   ```bash
   python server.py
   ```

5. Open your browser and navigate to `http://localhost:8000`

## Deployment to Vercel

The application is configured for deployment on Vercel's serverless platform.

### Important Considerations

1. **Database**: The SQLite database is stored in the `/tmp` directory on Vercel, which is ephemeral. For production use, consider migrating to a cloud database solution.

2. **Environment Variables**: Set the following environment variables in your Vercel project settings:
   - `OPENAI_API_KEY`: Your OpenAI API key

3. **Deployment Steps**:
   - Install Vercel CLI: `npm i -g vercel`
   - Login to Vercel: `vercel login`
   - Deploy: `vercel`
   - For production deployment: `vercel --prod`

4. **Limitations**:
   - Execution time limit: 10 seconds (Hobby plan)
   - Memory limit: 1024MB
   - Cold starts may affect performance

For more detailed information about Vercel deployment, see the `VERCEL_DEPLOYMENT_NOTES.md` file.

## Project Structure

- `server.py`: Main FastAPI application
- `frontend/`: Static files for the web interface
- `backend/`: Backend API and business logic
  - `api/`: API endpoints
  - `db/`: Database operations
  - `chains/`: LangChain components
- `api/`: Vercel serverless function entry point

## License

[MIT License](LICENSE) 