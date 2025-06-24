import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

// GET handler to fetch current privacy filters
export async function GET() {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ error: "Could not create auth header" },
			{ status: 500 }
		)
	}

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
		console.error("API Error in /settings/filters (GET):", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
}

// POST handler to update privacy filters
export async function POST(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ error: "Could not create auth header" },
			{ status: 500 }
		)
	}

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
		console.error("API Error in /settings/filters (POST):", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
}
