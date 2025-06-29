#!/bin/bash
set -e

echo "Running User Service tests..."
pytest services/user_service/tests

echo "Running Document Service tests..."
pytest services/document_service/tests

echo "Running Collaboration Service tests..."
pytest services/collaboration_service/tests 