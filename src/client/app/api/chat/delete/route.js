// src/client/app/api/chat/delete/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { message_id?: string, clear_all?: boolean }

		const backendResponse = await fetch(`${appServerUrl}/chat/delete`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(body)
		})

		const data = await backendResponse.json()

		if (!backendResponse.ok) {
			throw new Error(data.detail || "Failed to delete message(s)")
		}

		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /chat/delete:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
})
