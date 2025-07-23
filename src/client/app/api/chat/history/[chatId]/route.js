// src/client/app/api/chat/history/[chatId]/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const GET = withAuth(async function GET(
	request,
	{ params, authHeader }
) {
	const { chatId } = params
	if (!chatId) {
		return NextResponse.json(
			{ error: "Chat ID parameter is required" },
			{ status: 400 }
		)
	}

	try {
		const response = await fetch(`${appServerUrl}/chat/history/${chatId}`, {
			headers: { "Content-Type": "application/json", ...authHeader }
		})
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch chat messages")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
