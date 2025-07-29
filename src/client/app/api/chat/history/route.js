// src/client/app/api/chat/history/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const { searchParams } = new URL(request.url)
		const limit = searchParams.get("limit")
		const before_timestamp = searchParams.get("before_timestamp")

		const url = new URL(`${appServerUrl}/chat/history`)
		if (limit) url.searchParams.append("limit", limit)
		if (before_timestamp)
			url.searchParams.append("before_timestamp", before_timestamp)

		const response = await fetch(url.toString(), {
			method: "GET",
			headers: { "Content-Type": "application/json", ...authHeader }
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch chat history")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /chat/history:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
