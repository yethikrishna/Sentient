import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.INTERNAL_APP_SERVER_URL ||
	process.env.NEXT_PUBLIC_APP_SERVER_URL

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(`${appServerUrl}/integrations/sources`, {
			method: "GET",
			headers: { "Content-Type": "application/json", ...authHeader }
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch integrations")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /settings/integrations:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
