// src/client/app/api/tasks/add/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const taskData = await request.json()
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/agents/add-task`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(taskData)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to add task")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/add:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
