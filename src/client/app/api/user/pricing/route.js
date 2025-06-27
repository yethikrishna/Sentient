// src/client/app/api/user/pricing/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		// This single backend call can fetch all pricing-related info
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/api/get-user-data`,
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
})
