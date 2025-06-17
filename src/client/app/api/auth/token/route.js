import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"

/**
 * API route to securely get the user's access token from their session.
 * This is used by the client-side WebSocket to get a token for authentication.
 */
export async function GET() {
	try {
		const tokenResult = await auth0.getAccessToken()
		// Handle both `accessToken` and `token` properties for robustness
		const token = tokenResult?.accessToken || tokenResult?.token
		if (!token) {
			return NextResponse.json(
				{ message: "Not authenticated or access token is missing" },
				{ status: 401 }
			)
		}
		return NextResponse.json({ accessToken: token })
	} catch (error) {
		console.error("Error in /api/auth/token:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
}
