// src/client/app/api/tasks/update/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const taskData = await request.json()
		const response = await fetch(`${appServerUrl}/tasks/update-task`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(taskData)
		})

		if (!response.ok) {
			const errorText = await response.text()
			let detail = "Failed to update task"
			try {
				const errorJson = JSON.parse(errorText)
				detail = errorJson.detail || errorJson.error || errorText
			} catch (e) {}
			return NextResponse.json(
				{ error: detail },
				{ status: response.status }
			)
		}
		const data = await response.json()
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/update:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
