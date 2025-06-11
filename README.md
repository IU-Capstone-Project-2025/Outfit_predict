# Outfit Predict
Web-platform that helps users to decide which outfit to wear based on person's wardrobe and clothing of characters from movies, fashions collections, fashion markets.

## Getting Started

### Environment Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Update the `.env` file with your configuration values.

### Running the Application

To run the application using Docker Compose:

```bash
# Build and start all services
docker-compose up --build

# To run in detached mode (in the background)
docker-compose up --build -d

# To stop all services
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- MinIO Console: http://localhost:9001
