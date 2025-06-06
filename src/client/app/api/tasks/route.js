// src/client/app/api/tasks/route.js
import { NextResponse } from "next/server"
import { getSession, getBackendAuthHeader } from "@/lib/auth"

export async function GET() {
	const session = await getSession()
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
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/agents/fetch-tasks`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to fetch tasks")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
