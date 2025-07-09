#!/usr/bin/env sh

echo "Waiting for 5 seconds for the database to start..."
sleep 5

echo "Running database migrations."
alembic upgrade head

echo "Starting application."
exec "$@"