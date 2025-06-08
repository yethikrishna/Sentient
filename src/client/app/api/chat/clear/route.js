// src/client/app/api/chat/clear/route.js
import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"
import { getBackendAuthHeader } from "@lib/auth0"

export async function POST() {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ message: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ message: "Could not create auth header" },
			{ status: 500 }
		)
	}

	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/clear-chat-history`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.message || "Failed to clear chat history")
		}

		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /chat/clear:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
}
