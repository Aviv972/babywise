# Vercel Deployment Notes for Babywise Assistant

This document outlines important considerations and potential issues when deploying the Babywise Assistant to Vercel.

## Serverless Function Limitations

### Cold Starts
- Vercel serverless functions have cold starts, which may cause the first request to be slower
- Consider implementing a "keep-alive" mechanism for critical functions

### Execution Time Limits
- Vercel has a maximum execution time of 10 seconds for the Hobby plan
- Ensure that all API endpoints complete within this time limit
- For longer operations, consider implementing asynchronous processing

### Memory Limits
- The maximum memory allocation is 1024MB
- The `maxLambdaSize` is set to 15MB in the Vercel configuration

## Database Considerations

### SQLite on Vercel
- SQLite database files are stored in `/tmp` directory on Vercel
- This storage is ephemeral and will be cleared periodically
- Data will not persist between function invocations
- Consider migrating to a cloud database solution for production use

### Recommended Database Solutions
- **Supabase**: PostgreSQL database with a generous free tier
- **PlanetScale**: MySQL-compatible serverless database
- **MongoDB Atlas**: Document database with a free tier
- **Vercel Postgres**: Vercel's managed PostgreSQL service (paid)

## Environment Variables

- Ensure all required environment variables are set in the Vercel project settings
- Critical variables:
  - `OPENAI_API_KEY`: Required for LangChain and OpenAI API calls

## File System Access

- Vercel functions have read-only access to the deployment
- Writing to the file system is only possible in the `/tmp` directory
- Files in `/tmp` are not guaranteed to persist between function invocations

## API Routes

- All routes are directed to `api/index.py`
- The FastAPI app is imported from `server.py`
- Ensure that all API endpoints are properly prefixed with `/api`

## Frontend Serving

- Static files are served from the root directory
- The frontend files are served through the FastAPI app
- Ensure that the frontend files are properly included in the deployment

## Potential Issues and Solutions

### Issue: Database Persistence
- **Problem**: SQLite database is stored in ephemeral storage
- **Solution**: Migrate to a cloud database solution

### Issue: Long-Running Operations
- **Problem**: Vercel has a 10-second execution time limit
- **Solution**: Implement asynchronous processing or background tasks

### Issue: Large Dependencies
- **Problem**: The deployment package size is limited
- **Solution**: Optimize dependencies and consider splitting into multiple functions

### Issue: Cold Starts
- **Problem**: First request after inactivity may be slow
- **Solution**: Implement a "keep-alive" mechanism or use a paid plan with reserved concurrency

## Monitoring and Debugging

- Use Vercel's built-in logging for debugging
- Consider implementing additional logging with a service like Sentry
- Monitor function execution times and memory usage

## Scaling Considerations

- Vercel automatically scales based on demand
- For high-traffic applications, consider upgrading to a paid plan
- Implement caching for frequently accessed data

## Conclusion

Vercel is a great platform for deploying the Babywise Assistant, but it's important to be aware of the limitations of serverless functions. For a production deployment, consider migrating to a cloud database solution and implementing strategies to handle cold starts and execution time limits. 