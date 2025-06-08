// src/client/app/api/user/pricing/route.js
import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"
import { getBackendAuthHeader } from "@lib/auth0"

export async function GET() {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ message: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ message: "Could not create auth header" },
			{ status: 500 }
		)
	}

	try {
		// This single backend call can fetch all pricing-related info
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/get-user-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.message || "Failed to fetch user data from backend"
			)
		}

		// Extract pricing and credits from the user data response
		const pricing = data?.data?.pricing || "free"
		const credits = data?.data?.proCredits || 0

		return NextResponse.json({ pricing, credits })
	} catch (error) {
		console.error("API Error in /user/pricing:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
}
