import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const chatData = await request.json() // this will be { taskId, message }
		const response = await fetch(`${appServerUrl}/tasks/task-chat`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(chatData)
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to send chat message")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/chat:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
