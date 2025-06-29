#!/bin/bash
set -e

python3 -m venv venv
source venv/bin/activate
pip install -r services/user_service/requirements.txt
pip install -r services/document_service/requirements.txt
pip install -r services/collaboration_service/requirements.txt

echo "\nLocal setup complete. To start all services:"
echo "docker-compose up --build" 