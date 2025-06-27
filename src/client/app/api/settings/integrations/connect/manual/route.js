import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const POST = withAuth(async function POST(request, { authHeader }) {
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
})
