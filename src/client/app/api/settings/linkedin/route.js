import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(`${appServerUrl}/api/settings/linkedin`, {
			method: "GET",
			headers: { "Content-Type": "application/json", ...authHeader }
		})
		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch LinkedIn settings")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /api/settings/linkedin (GET):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { linkedin_url: "..." }
		const response = await fetch(`${appServerUrl}/api/settings/linkedin`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(body)
		})

		const data = await response.json()
		if (!response.ok) {
			// Forward the specific error message from the backend
			throw new Error(data.detail || "Failed to update LinkedIn URL")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /api/settings/linkedin (POST):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
