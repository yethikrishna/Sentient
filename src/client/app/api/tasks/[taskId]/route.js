import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

const APP_SERVER_URL = process.env.APP_SERVER_URL

// GET: Fetch a single task by its ID
export async function GET(request, { params }) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const { taskId } = params
	if (!taskId) {
		return NextResponse.json(
			{ error: "Task ID parameter is required" },
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
			`${APP_SERVER_URL}/agents/tasks/${taskId}`,
			{
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch task details")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
