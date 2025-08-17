// src/client/app/api/tasks/add/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const taskData = await request.json()
		const response = await fetch(`${appServerUrl}/tasks/add-task`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(taskData)
		})

		const data = await response.json()
		if (!response.ok) {
			// Propagate the error and status code from the backend directly
			return NextResponse.json(
				{ error: data.detail || "Failed to add task" },
				{ status: response.status }
			)
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/add:", error)
		// This catch is for network errors or if JSON parsing fails
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
