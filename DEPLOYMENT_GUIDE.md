# Babywise Assistant Deployment Guide

This guide provides step-by-step instructions for deploying the Babywise Assistant to Vercel.

## Prerequisites

- A [Vercel](https://vercel.com) account
- [Node.js](https://nodejs.org) installed (for Vercel CLI)
- An [OpenAI API key](https://platform.openai.com/api-keys)
- Git installed

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository contains all the necessary files:
- `vercel.json` - Vercel configuration
- `api/index.py` - Vercel entry point
- `api/requirements.txt` - Dependencies for Vercel

### 2. Install Vercel CLI

```bash
npm install -g vercel
```

### 3. Login to Vercel

```bash
vercel login
```

### 4. Deploy to Vercel

Navigate to your project directory and run:

```bash
vercel
```

Follow the prompts:
- Set up and deploy? `y`
- Which scope? Select your account
- Link to existing project? `n`
- Project name? `babywise-assistant` (or your preferred name)
- Directory? `.` (current directory)

### 5. Set Environment Variables

After the initial deployment, set up your environment variables:

1. Go to the [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to "Settings" > "Environment Variables"
4. Add the following variables:
   - `OPENAI_API_KEY`: Your OpenAI API key

### 6. Deploy to Production

After setting up environment variables, deploy to production:

```bash
vercel --prod
```

## Important Considerations

### Database Persistence

The SQLite database is stored in the `/tmp` directory on Vercel, which is ephemeral. This means:
- Data will not persist between function invocations
- The database will be cleared periodically

For production use, consider migrating to a cloud database solution such as:
- Supabase (PostgreSQL)
- PlanetScale (MySQL)
- MongoDB Atlas
- Vercel Postgres

### Execution Time Limits

Vercel has a maximum execution time of 10 seconds for the Hobby plan. Ensure that all API endpoints complete within this time limit.

### Cold Starts

Vercel serverless functions have cold starts, which may cause the first request after a period of inactivity to be slower.

## Troubleshooting

### 502 Bad Gateway

If you encounter a 502 Bad Gateway error:
- Check your environment variables
- Ensure your dependencies are correctly specified in `api/requirements.txt`
- Check the function logs in the Vercel dashboard

### Function Timeout

If your function times out:
- Optimize your code to complete within the 10-second limit
- Consider implementing asynchronous processing for longer operations

### Database Issues

If you're experiencing database issues:
- Remember that the SQLite database is ephemeral on Vercel
- Consider migrating to a cloud database solution

## Monitoring

Monitor your deployment using the Vercel dashboard:
- Function invocations
- Error rates
- Response times

## Conclusion

Your Babywise Assistant should now be deployed and accessible via the Vercel URL. For a custom domain, you can configure it in the Vercel dashboard under "Settings" > "Domains". 