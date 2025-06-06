// src/client/app/api/memory/short-term/update/route.js
import { NextResponse } from "next/server"
import { getSession, getBackendAuthHeader } from "@/lib/auth"

export async function POST(request) {
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
		const memoryData = await request.json()
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/memory/update-short-term-memory`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(memoryData)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to update memory")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /memory/short-term/update:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
