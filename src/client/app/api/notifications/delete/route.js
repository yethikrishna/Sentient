import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const { notification_id } = await request.json()
		if (!notification_id) {
			return NextResponse.json(
				{ error: "Notification ID is required" },
				{ status: 400 }
			)
		}

		const response = await fetch(
			`${process.env.NEXT_PUBLIC_APP_SERVER_URL}/notifications/delete`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ notification_id })
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to delete notification")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /notifications/delete:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
