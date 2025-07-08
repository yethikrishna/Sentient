import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "SELFHOST"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET handler to fetch the current Supermemory MCP URL
export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(
			`${appServerUrl}/api/settings/supermemory`,
			{
				// Ensure GET is used for fetching data
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.detail ||
					data.error ||
					"Failed to fetch Supermemory settings"
			)
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /settings/mcp (GET):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// POST handler to save the Supermemory MCP URL
export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { mcp_url: "..." }
		const backendResponse = await fetch(
			// Renamed to avoid conflict with API response
			`${appServerUrl}/api/settings/supermemory`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await backendResponse.json()
		if (!backendResponse.ok) {
			throw new Error(
				data.detail ||
					data.error ||
					"Failed to save Supermemory settings"
			)
		}
		return NextResponse.json(data) // Return the backend's response directly
	} catch (error) {
		console.error("API Error in /settings/mcp (POST):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
