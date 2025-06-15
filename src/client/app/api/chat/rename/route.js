import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

export async function POST(request) {
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
		const body = await request.json() // { chatId, newTitle }
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/rename-chat`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to rename chat")
		}

		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /chat/rename:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
}
