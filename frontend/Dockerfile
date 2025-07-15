# Use the official Node.js image
FROM node:18-alpine

# Install pnpm
RUN npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# Copy source code
COPY . .


# Used for passing the backend API url to frontend.
# The problem with previous implementation is that the baseUrl is actually loaded during pnpm build
# But during build, the frontend container does not receive the environment variable, it does so
# only after the container is built, and orchestrating is running. Therefore, we defined this argument
# so that we have a mechanism to pass the environment variable from docker compose to frontend at build time.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the application
RUN pnpm build

# Expose port 3000
EXPOSE 3000

# Start the application
CMD ["pnpm", "start"]
