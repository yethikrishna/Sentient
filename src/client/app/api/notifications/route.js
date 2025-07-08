// src/client/app/api/notifications/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(
			`${process.env.NEXT_PUBLIC_APP_SERVER_URL}/notifications/`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to fetch notifications")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /notifications:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
