// src/client/app/api/auth/[auth0]/route.js
import { handleAuth } from "@auth0/nextjs-auth0"

// By exporting `handleAuth` directly for both GET and POST methods,
// we let the Auth0 SDK handle the request and context (including params)
// in a way that is compatible with modern Next.js.
// This single handler will correctly manage all sub-routes like /login, /logout, /callback, and /me.
// The POST export is crucial for the /api/auth/callback route to work correctly.
const authHandler = handleAuth()

export const GET = authHandler

export const POST = authHandler
