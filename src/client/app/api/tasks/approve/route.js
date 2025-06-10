// src/client/app/api/tasks/approve/route.js
import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"
import { getBackendAuthHeader } from "@lib/auth0"

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
		const { taskId } = await request.json()
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/agents/approve-task`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ taskId: taskId })
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to approve task")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/approve:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
