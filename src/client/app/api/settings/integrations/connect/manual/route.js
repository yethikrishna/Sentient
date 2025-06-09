import { NextResponse } from "next/server"
import { getBackendAuthHeader, auth0 } from "@lib/auth0"

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
		const body = await request.json() // { service_name, credentials }
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/integrations/connect/manual`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to connect integration")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error(
			"API Error in /settings/integrations/connect/manual:",
			error
		)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
