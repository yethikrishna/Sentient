// src/client/app/api/memory/long-term/customize/route.js
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
		const { newGraphInfo } = await request.json()
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/memory/customize-long-term-memories`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ information: newGraphInfo })
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to customize graph")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /memory/long-term/customize:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
