#!/bin/bash
set -e

# Migrate User Service DB
cd ../services/user_service
alembic upgrade head
cd -

# Migrate Document Service DB
cd ../services/document_service
alembic upgrade head
cd - 