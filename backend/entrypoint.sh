#!/usr/bin/env sh

echo "Waiting for 5 seconds for the database to start..."
sleep 5

echo "Running database migrations."
if ! alembic upgrade head; then
    echo "Migration failed. Attempting to stamp the database with current revision..."
    # If migration fails, try to stamp with the latest revision to recover
    alembic stamp head
    echo "Database stamped. Application will start but may have schema issues."
else
    echo "Migrations completed successfully."
fi

echo "Starting application."
exec "$@"
