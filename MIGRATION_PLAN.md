# Migration Plan for Babywise Assistant

This document outlines the plan for migrating the Babywise Assistant project to a new Git repository with Vercel integration.

## Pre-Migration Checklist

- [x] Create Vercel-compatible entry point (`api/index.py`)
- [x] Create Vercel configuration file (`vercel.json`)
- [x] Update README.md with Vercel deployment information
- [x] Create requirements.txt for Vercel in the api directory
- [x] Ensure all necessary files are included in the repository
- [ ] Test the application locally to ensure it works as expected
- [ ] Verify that the database functionality works correctly
- [ ] Check that all API endpoints are accessible
- [ ] Ensure that the frontend is properly served

## Migration Steps

1. **Create a new Git repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Babywise Assistant"
   ```

2. **Connect to the remote repository**
   ```bash
   git remote add origin https://github.com/yourusername/babywise-assistant.git
   git push -u origin main
   ```

3. **Set up Vercel integration**
   - Connect the GitHub repository to Vercel
   - Add the following environment variables in Vercel:
     - `OPENAI_API_KEY`: Your OpenAI API key
   - Deploy the project

4. **Verify deployment**
   - Check that the application is accessible at the Vercel URL
   - Test the chat functionality
   - Test the routine tracking functionality
   - Verify that the database is working correctly

## Post-Migration Tasks

- [ ] Update DNS records if using a custom domain
- [ ] Set up monitoring and logging
- [ ] Configure automatic backups for the database
- [ ] Document any issues encountered during migration
- [ ] Create a development branch for future work

## Rollback Plan

If the migration fails or encounters critical issues:

1. Revert to the previous repository
2. Document the issues encountered
3. Create a new migration plan addressing the issues

## Notes

- The Vercel deployment uses Python 3.9 runtime
- The maximum Lambda size is set to 15MB
- All routes are directed to the `api/index.py` entry point
- The database is SQLite, which is stored in the `/tmp` directory on Vercel
- For persistent storage, consider migrating to a cloud database solution in the future 