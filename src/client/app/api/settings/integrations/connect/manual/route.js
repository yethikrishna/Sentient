import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { service_name, credentials }
		const response = await fetch(
			`${appServerUrl}/integrations/connect/manual`,
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
