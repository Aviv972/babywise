#!/bin/bash

# Create backup directory
BACKUP_DIR="./backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR/src/agents"
mkdir -p "$BACKUP_DIR/src/services"
mkdir -p "$BACKUP_DIR/src/tests"
mkdir -p "$BACKUP_DIR/tests"

echo "Creating backups in $BACKUP_DIR..."

# Backup and remove agent files
echo "Backing up agent files..."
cp -r src/agents/* "$BACKUP_DIR/src/agents/"
# Keep the __init__.py file
touch src/agents/__init__.py.keep
# Remove agent files
rm -f src/agents/*.py
# Restore __init__.py
mv src/agents/__init__.py.keep src/agents/__init__.py

# Backup and remove service files
echo "Backing up service files..."
cp -r src/services/* "$BACKUP_DIR/src/services/"
# Keep the __init__.py file
touch src/services/__init__.py.keep
# Remove service files
rm -f src/services/agent_factory.py
rm -f src/services/agent_router.py
rm -f src/services/chat_session.py
rm -f src/services/llm_service.py
rm -f src/services/memory_service.py
rm -f src/services/service_container.py
rm -f src/services/semantic_matcher.py
# Restore __init__.py
mv src/services/__init__.py.keep src/services/__init__.py

# Backup and remove CLI test
echo "Backing up CLI test..."
if [ -f src/cli_test.py ]; then
  cp src/cli_test.py "$BACKUP_DIR/src/"
  rm -f src/cli_test.py
fi

# Backup and remove agent-related test files
echo "Backing up test files..."
if [ -d src/tests ]; then
  cp -r src/tests/* "$BACKUP_DIR/src/tests/" 2>/dev/null || true
  rm -f src/tests/test_*agent*.py
fi

if [ -d tests ]; then
  cp -r tests/* "$BACKUP_DIR/tests/" 2>/dev/null || true
  rm -f tests/test_*agent*.py
fi

echo "Cleanup complete. Files have been backed up to $BACKUP_DIR"
echo "You can restore files from the backup if needed." 