// src/client/app/api/tasks/approval-data/route.js
import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"
import { getBackendAuthHeader } from "@lib/auth0"

export async function GET(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const { searchParams } = new URL(request.url)
	const taskId = searchParams.get("taskId")
	if (!taskId) {
		return NextResponse.json(
			{ error: "Task ID is required" },
			{ status: 400 }
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
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/agents/get-task-approval-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ task_id: taskId })
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to fetch approval data")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/approval-data:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
