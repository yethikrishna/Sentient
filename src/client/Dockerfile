# src/client/Dockerfile

# 1. Builder Stage: Installs dependencies and builds the app
FROM node:20-slim AS builder
WORKDIR /app

# Copy package.json and lock file to leverage Docker cache
COPY package.json ./
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the Next.js application for production
# This creates the .next/standalone folder
RUN npm run build


# 2. Runner Stage: Creates the final, lightweight image
FROM node:20-alpine AS runner
WORKDIR /app

# Set the environment to production
ENV NODE_ENV=production
ENV PORT=3000

# Copy the standalone Next.js server from the builder stage
COPY --from=builder /app/.next/standalone ./
# Copy public assets and static build artifacts
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static

# Expose the port the app will run on
EXPOSE 3000

# The command to start the optimized Next.js server
CMD ["node", "server.js"]