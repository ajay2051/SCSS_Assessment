#!/bin/bash
set -e

# Wait for database
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do
      echo "==========👌🙏🔥 PostgreSQL is unavailable - sleeping 👌🙏🔥=========="
      sleep 1
    done
    echo "=================👌🙏🔥 PostgreSQL started 👌🙏🔥================="
fi


# Add a small delay to ensure services are ready
sleep 2

echo "================================👌🙏🔥 Server is starting now 👌🙏🔥=================================="

echo "================================👌🙏🔥 Applying Migrations 👌🙏🔥=================================="

python3 manage.py migrate

# Start Django Sever
echo "===================👌🙏🔥 Starting Django server 👌🙏🔥============================"
#exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
gunicorn --bind 0.0.0.0:8000 --reload project.wsgi
