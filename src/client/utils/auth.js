// src/client/lib/auth.js
import { headers } from "next/headers"
import { jwtDecode } from "jwt-decode"

/**
 * A server-side helper to simulate retrieving the current user's session.
 * In a real application, this would be replaced by your authentication provider's
 * method, for example, `getServerSession` from `next-auth`.
 *
 * It simulates extracting a JWT from the Authorization header, decoding it,
 * and returning the user's profile information.
 *
 * @returns {Promise<object|null>} A promise that resolves to the user session object or null if not authenticated.
 */
export async function getSession() {
	const authHeader = headers().get("Authorization")

	if (!authHeader || !authHeader.startsWith("Bearer ")) {
		// In a real app with NextAuth.js, you'd get the session from cookies, not headers.
		// For this mock, we'll return a default user if no header is present,
		// to allow the app to function without a real login flow.
		console.warn("lib/auth: No Auth header found. Returning mock session.")
		return {
			user: {
				id: "mock-user-123",
				name: "Mock User",
				email: "user@example.com",
				// This 'sub' is what the original app used as userId
				sub: "auth0|mock-user-123"
			},
			accessToken: "mock-access-token-for-backend-calls"
		}
	}

	try {
		const token = authHeader.split(" ")[1]
		const decoded = jwtDecode(token)
		return {
			user: decoded,
			accessToken: token
		}
	} catch (error) {
		console.error("lib/auth: Error decoding token:", error)
		return null
	}
}

/**
 * A server-side helper to construct the Authorization header for backend API calls.
 * It retrieves the session and uses the access token from it.
 *
 * @returns {Promise<{ Authorization: string }|null>} An object with the Authorization header or null if no token is available.
 */
export async function getBackendAuthHeader() {
	const session = await getSession()
	const token = session?.accessToken

	if (!token) {
		console.error(
			"lib/auth: Cannot create backend auth header, access token is missing."
		)
		return null
	}
	return { Authorization: `Bearer ${token}` }
}
