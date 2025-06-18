import { NextResponse } from "next/server"
import { getBackendAuthHeader, auth0 } from "@lib/auth0"

// GET handler to fetch the current Supermemory MCP URL
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
			`${process.env.APP_SERVER_URL}/api/settings/supermemory`,
			{
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.detail || "Failed to fetch Supermemory settings"
			)
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /settings/mcp (GET):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}

// POST handler to save the Supermemory MCP URL
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
		const body = await request.json() // { mcp_url: "..." }
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/api/settings/supermemory`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.detail || "Failed to save Supermemory settings"
			)
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /settings/mcp (POST):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
