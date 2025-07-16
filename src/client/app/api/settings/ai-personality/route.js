import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET handler to fetch current AI personality settings
export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(
			`${appServerUrl}/api/settings/ai-personality`,
			{
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch AI settings")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /api/settings/ai-personality (GET):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// POST handler to update AI personality settings
export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json()
		const response = await fetch(
			`${appServerUrl}/api/settings/ai-personality`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to update AI settings")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error(
			"API Error in /api/settings/ai-personality (POST):",
			error
		)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
