// src/client/app/api/tasks/approve/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const { taskId } = await request.json()
		const response = await fetch(`${appServerUrl}/tasks/approve-task`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify({ taskId: taskId })
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to approve task")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/approve:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
