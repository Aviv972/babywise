#!/bin/bash

# Build script for Vercel deployment
# Ensures proper handling of static assets and RTL support for Hebrew language

echo "Starting build process..."

# Create necessary directories
mkdir -p public

# Copy static files to public directory
echo "Copying frontend files..."
cp -r frontend/* public/

# Copy static assets
echo "Copying static assets..."
if [ -d "static/css" ]; then
  mkdir -p public/css
  cp -r static/css/* public/css/
fi

if [ -d "static/js" ]; then
  mkdir -p public/js
  cp -r static/js/* public/js/
fi

if [ -d "static/images" ]; then
  mkdir -p public/images
  cp -r static/images/* public/images/
fi

if [ -d "static/frontend" ]; then
  cp -r static/frontend/* public/
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
    sed -i.bak 's/<html/<html dir="auto"/' "public/index.html"
    rm -f "public/index.html.bak"
  else
    echo "RTL support already in place in index.html"
  fi
fi

# Ensure CSS for RTL support is included
if [ -f "public/style.css" ]; then
  # Check if RTL CSS rules are already in place
  if ! grep -q '\.rtl' "public/style.css"; then
    echo "Adding RTL CSS rules to style.css..."
    cat >> "public/style.css" << EOF

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
  else
    echo "RTL CSS rules already in place in style.css"
  fi
fi

echo "Build completed successfully!" 