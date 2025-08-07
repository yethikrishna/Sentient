// src/client/app/api/integrations/gcalendar/events/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const GET = withAuth(async function GET(request, { authHeader }) {
	const { searchParams } = new URL(request.url)
	const startDate = searchParams.get("start_date")
	const endDate = searchParams.get("end_date")

	if (!startDate || !endDate) {
		return NextResponse.json(
			{ error: "start_date and end_date are required" },
			{ status: 400 }
		)
	}

	const backendUrl = new URL(`${appServerUrl}/integrations/gcalendar/events`)
	backendUrl.searchParams.append("start_date", startDate)
	backendUrl.searchParams.append("end_date", endDate)

	try {
		const response = await fetch(backendUrl.toString(), {
			method: "GET",
			headers: { "Content-Type": "application/json", ...authHeader }
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.detail || "Failed to fetch Google Calendar events"
			)
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /integrations/gcalendar/events:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
