// src/client/app/api/integrations/connected/route.js
import { NextResponse } from "next/server"
import { getBackendAuthHeader, auth0 } from "@lib/auth0"

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
		// This reuses the same backend endpoint but we will filter on the client
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/integrations/sources`,
			{
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch integrations")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /integrations/connected:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
