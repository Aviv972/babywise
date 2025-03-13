#!/bin/bash

# Script to push Babywise fixes to Git

echo "Pushing Babywise fixes to Git..."

# Make sure we're in the project root
cd "$(dirname "$0")"

# Ensure we have the latest code
echo "Committing changes..."
git add .
git commit -m "Fix HumanMessage import and LangChain serialization issues"

# Push changes to the remote repository
echo "Pushing to Git repository..."
git push

echo "Changes pushed successfully!" 