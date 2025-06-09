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
		console.error("API Error in /settings/integrations:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
