import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const GET = withAuth(async function GET(request, { authHeader }) {
	const { searchParams } = new URL(request.url)
	const date = searchParams.get("date")

	try {
		const url = date
			? `${appServerUrl}/notes/?date=${date}`
			: `${appServerUrl}/notes/`
		const response = await fetch(url, {
			method: "GET",
			headers: { "Content-Type": "application/json", ...authHeader }
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch notes")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /api/notes (GET):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { title, content, note_date }
		const response = await fetch(`${appServerUrl}/notes/`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(body)
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to create note")
		}
		return NextResponse.json(data, { status: 201 })
	} catch (error) {
		console.error("API Error in /api/notes (POST):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
