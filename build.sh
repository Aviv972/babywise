#!/bin/bash

# Build script for Vercel deployment
# Ensures proper handling of static assets and RTL support for Hebrew language

set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting build process..."
echo "Current directory: $(pwd)"
echo "Directory contents: $(ls -la)"

# Create necessary directories
mkdir -p public
echo "Created public directory"

# Copy static files to public directory
echo "Copying frontend files..."
if [ -d "frontend" ]; then
  cp -r frontend/* public/ || { echo "Error copying frontend files"; exit 1; }
  echo "Frontend files copied successfully"
  echo "Public directory contents: $(ls -la public)"
else
  echo "Warning: frontend directory not found"
fi

# Copy static assets
echo "Copying static assets..."
if [ -d "static/css" ]; then
  mkdir -p public/css
  cp -r static/css/* public/css/ || { echo "Error copying CSS files"; exit 1; }
  echo "CSS files copied successfully"
fi

if [ -d "static/js" ]; then
  mkdir -p public/js
  cp -r static/js/* public/js/ || { echo "Error copying JS files"; exit 1; }
  echo "JS files copied successfully"
fi

if [ -d "static/images" ]; then
  mkdir -p public/images
  cp -r static/images/* public/images/ || { echo "Error copying image files"; exit 1; }
  echo "Image files copied successfully"
fi

if [ -d "static/frontend" ]; then
  cp -r static/frontend/* public/ || { echo "Error copying static frontend files"; exit 1; }
  echo "Static frontend files copied successfully"
fi

# Ensure RTL support for Hebrew language
echo "Ensuring RTL support for Hebrew language..."
# Add dir="auto" attribute to relevant HTML elements if not already present
if [ -f "public/index.html" ]; then
  # Check if RTL support is already in place
  if ! grep -q 'dir="auto"' "public/index.html"; then
    echo "Adding RTL support to index.html..."
    # This is a simple sed command to add dir="auto" to the html tag
    # For a more comprehensive solution, a proper HTML parser would be needed
    sed -i.bak 's/<html/<html dir="auto"/' "public/index.html" || { echo "Error adding RTL support to HTML"; exit 1; }
    rm -f "public/index.html.bak"
    echo "RTL support added to index.html"
  else
    echo "RTL support already in place in index.html"
  fi
else
  echo "Warning: index.html not found in public directory"
  echo "Public directory contents: $(ls -la public)"
fi

# Ensure CSS for RTL support is included
if [ -f "public/style.css" ]; then
  # Check if RTL CSS rules are already in place
  if ! grep -q '\.rtl' "public/style.css"; then
    echo "Adding RTL CSS rules to style.css..."
    cat >> "public/style.css" << EOF || { echo "Error adding RTL CSS rules"; exit 1; }

/* RTL Support for Hebrew language */
.rtl {
  direction: rtl;
  text-align: right;
}

.rtl .message-bubble.user {
  margin-left: 0;
  margin-right: auto;
}

.rtl .message-bubble.assistant {
  margin-right: 0;
  margin-left: auto;
}

.rtl .timestamp {
  left: auto;
  right: 8px;
}
EOF
    echo "RTL CSS rules added to style.css"
  else
    echo "RTL CSS rules already in place in style.css"
  fi
else
  echo "Warning: style.css not found in public directory"
fi

echo "Build completed successfully!" 