import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

// GET handler to fetch current privacy filters
export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		// We can get this from the get-user-data endpoint
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/api/get-user-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		if (!response.ok) {
			throw new Error("Failed to fetch user data from backend.")
		}

		const data = await response.json()
		const filters = data?.data?.privacyFilters || []

		return NextResponse.json({ filters })
	} catch (error) {
		console.error("API Error in /settings/privacy-filters (GET):", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
})

// POST handler to update privacy filters
export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const { filters } = await request.json()
		if (!Array.isArray(filters)) {
			return NextResponse.json(
				{
					error: "Invalid filters format. Expected an array of strings."
				},
				{ status: 400 }
			)
		}

		const backendResponse = await fetch(
			`${process.env.APP_SERVER_URL}/api/settings/privacy-filters`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ filters: filters })
			}
		)

		const data = await backendResponse.json()
		if (!backendResponse.ok) {
			throw new Error(data.detail || "Failed to update privacy filters.")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /settings/privacy-filters (POST):", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
})
