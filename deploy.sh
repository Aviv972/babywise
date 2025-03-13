#!/bin/bash

# Deployment script for Babywise to Vercel

echo "Deploying Babywise to Vercel..."

# Make sure we're in the project root
cd "$(dirname "$0")"

# Ensure we have the latest code
echo "Committing changes..."
git add .
git commit -m "Fix HumanMessage import and LangChain serialization issues"

# Deploy to Vercel
echo "Deploying to Vercel..."
vercel --prod

echo "Deployment complete!" 