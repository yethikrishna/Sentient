// src/client/app/api/memory/short-term/route.js
import { NextResponse } from "next/server"
import { getSession, getBackendAuthHeader } from "@/lib/auth"

export async function GET(request) {
	const session = await getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const { searchParams } = new URL(request.url)
	const category = searchParams.get("category")
	const limit = searchParams.get("limit") || 10

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ error: "Could not create auth header" },
			{ status: 500 }
		)
	}

	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/memory/get-short-term-memories`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ category, limit: parseInt(limit) })
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to fetch short-term memories")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /memory/short-term:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
}
