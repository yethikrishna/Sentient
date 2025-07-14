# src/client/Dockerfile

# 1. Builder Stage: Installs dependencies and builds the app
FROM node:20-slim AS builder
WORKDIR /app

# ---- MODIFIED SECTION ----
# Declare all build-time arguments that your application needs.
# Anything prefixed with NEXT_PUBLIC_ is needed for the client-side bundle.
# Others are needed for server-side logic during the build (if any).
ARG NEXT_PUBLIC_APP_SERVER_URL
ARG AUTH0_SECRET
ARG INTERNAL_APP_SERVER_URL
ARG NEXT_PUBLIC_ENVIRONMENT
ARG SELF_HOST_AUTH_TOKEN
ARG APP_BASE_URL
ARG AUTH0_ISSUER_BASE_URL
ARG AUTH0_DOMAIN
ARG AUTH0_CLIENT_ID
ARG AUTH0_CLIENT_SECRET
ARG AUTH0_AUDIENCE
ARG AUTH0_SCOPE

# Set them as environment variables for the build process
ENV NEXT_PUBLIC_APP_SERVER_URL=$NEXT_PUBLIC_APP_SERVER_URL
ENV AUTH0_SECRET=$AUTH0_SECRET
ENV INTERNAL_APP_SERVER_URL=$INTERNAL_APP_SERVER_URL
ENV NEXT_PUBLIC_ENVIRONMENT=$NEXT_PUBLIC_ENVIRONMENT
ENV SELF_HOST_AUTH_TOKEN=$SELF_HOST_AUTH_TOKEN
ENV APP_BASE_URL=$APP_BASE_URL
ENV AUTH0_ISSUER_BASE_URL=$AUTH0_ISSUER_BASE_URL
ENV AUTH0_DOMAIN=$AUTH0_DOMAIN
ENV AUTH0_CLIENT_ID=$AUTH0_CLIENT_ID
ENV AUTH0_CLIENT_SECRET=$AUTH0_CLIENT_SECRET
ENV AUTH0_AUDIENCE=$AUTH0_AUDIENCE
ENV AUTH0_SCOPE=$AUTH0_SCOPE
# --------------------------

# Copy package.json and lock file to leverage Docker cache
COPY package.json ./
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the Next.js application for production
# This command will now have access to all the ENV vars
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

# The runner stage will get its env vars from the docker-compose 'env_file'
# The command to start the optimized Next.js server
CMD ["node", "server.js"]