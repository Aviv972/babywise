# Babywise Vercel Deployment Guide

This guide provides instructions for deploying the Babywise Assistant project on Vercel, ensuring compliance with project guidelines.

## Project Guidelines

The Babywise Assistant follows these key guidelines:

- **Multilingual Support**: Full Hebrew language support with RTL formatting
- **Asynchronous Programming**: All backend code uses async/await pattern
- **Redis Integration**: Cloud persistence using Redis for conversation state
- **WhatsApp-like UI**: Responsive design with proper RTL support
- **Routine Tracking**: SQLite database for baby routine data

## Deployment Configuration

The project is configured for Vercel deployment using the following files:

- `vercel.json`: Main configuration file for Vercel
- `api/index.py`: Serverless function entry point
- `build.sh`: Build script for static assets and RTL support
- `package.json`: Project metadata and build scripts

## Environment Variables

The following environment variables need to be set in the Vercel dashboard:

- `OPENAI_API_KEY`: Your OpenAI API key
- `STORAGE_URL`: Redis connection string
- `PYTHONPATH`: Set to `.` (root directory)
- `PYTHONUNBUFFERED`: Set to `1`

## Deployment Steps

1. Push your changes to GitHub
2. Vercel will automatically deploy from the GitHub repository
3. Check the deployment logs for any errors
4. Verify the application is working correctly

## RTL Support Verification

After deployment, verify RTL support is working correctly:

1. Test the application with Hebrew text input
2. Verify text alignment is right-to-left
3. Check that UI elements (message bubbles, timestamps) are properly positioned
4. Ensure the responsive design works on all device sizes

## Troubleshooting

### Function Runtime Error

If you encounter a "Function Runtimes must have a valid version" error:
- Ensure `vercel.json` specifies a valid runtime version (e.g., `@vercel/python@3.1.33`)
- Check that the `api/index.py` file exists and is properly formatted

### Missing Dependencies

If you encounter missing dependencies:
- Ensure `api/requirements.txt` includes all necessary packages
- Check that package versions are compatible with Vercel's environment

### Static Files Not Found

If static files are not being served:
- Verify the build script is running correctly
- Check that files are being copied to the `public` directory
- Ensure the `routes` configuration in `vercel.json` is correct

### RTL Support Issues

If RTL support is not working correctly:
- Check that the build script successfully added RTL CSS rules
- Verify HTML elements have the appropriate `dir="auto"` attribute
- Test with different browsers to ensure cross-browser compatibility

## Testing Locally

To test the deployment locally before pushing to Vercel:

1. Install the Vercel CLI: `npm install -g vercel`
2. Run `vercel dev` to start a local development server
3. Test the API endpoints and static file serving
4. Test RTL support with Hebrew text input

## Monitoring

After deployment, monitor the application using Vercel's dashboard:
- Check function execution logs
- Monitor API response times
- Set up alerts for errors

## Scaling

As your application grows:
- Consider using Vercel's Edge Functions for improved performance
- Set up multiple deployment regions
- Implement caching strategies for frequently accessed data
- Optimize Redis usage for better state persistence 