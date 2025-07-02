import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { prompt: "..." }
		const response = await fetch(
			`${process.env.NEXT_PUBLIC_APP_SERVER_URL}/agents/generate-plan`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to generate plan")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/generate-plan:", error)
		return NextResponse.json({ detail: error.message }, { status: 500 })
	}
})
