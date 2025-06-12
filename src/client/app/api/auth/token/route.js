import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"

/**
 * API route to securely get the user's access token from their session.
 * This is used by the client-side WebSocket to get a token for authentication.
 */
export async function GET() {
	try {
		const accessToken = await auth0.getAccessToken()
		if (!accessToken) {
			return NextResponse.json(
				{ message: "Not authenticated or access token is missing" },
				{ status: 401 }
			)
		}
		return NextResponse.json({ accessToken: accessToken })
	} catch (error) {
		console.error("Error getting access token from session:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
}
