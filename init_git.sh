#!/bin/bash

# Initialize Git repository for Babywise Assistant
echo "Initializing Git repository for Babywise Assistant..."

# Initialize Git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit for Babywise Assistant"

# Instructions for connecting to remote repository
echo ""
echo "Repository initialized successfully!"
echo ""
echo "To connect to your remote repository, run the following commands:"
echo "git remote add origin https://github.com/yourusername/babywise-assistant.git"
echo "git push -u origin main"
echo ""
echo "Make sure to replace 'yourusername' with your actual GitHub username."
echo ""
echo "After pushing to GitHub, you can connect the repository to Vercel for deployment."
echo "Don't forget to add your OPENAI_API_KEY as an environment variable in Vercel." 