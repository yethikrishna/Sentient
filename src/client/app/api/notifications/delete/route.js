import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

export async function POST(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ error: "Could not create auth header" },
			{ status: 500 }
		)
	}

	try {
		const { notification_id } = await request.json()
		if (!notification_id) {
			return NextResponse.json(
				{ error: "Notification ID is required" },
				{ status: 400 }
			)
		}

		const response = await fetch(
			`${process.env.APP_SERVER_URL}/notifications/delete`,
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
}
