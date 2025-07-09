import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const APP_SERVER_URL =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET: Fetch blocks for a specific date or date range
export const GET = withAuth(async function GET(request, { authHeader }) {
	const { searchParams } = new URL(request.url)
	const date = searchParams.get("date")
	const startDate = searchParams.get("startDate")
	const endDate = searchParams.get("endDate")

	let queryString = ""
	if (date) {
		queryString = `date=${date}`
	} else if (startDate && endDate) {
		// FIX: The backend FastAPI endpoint uses 'startDate' and 'endDate' as aliases for the query parameters.
		queryString = `startDate=${startDate}&endDate=${endDate}`
	} else {
		return NextResponse.json(
			{
				error: "Either 'date' or both 'startDate' and 'endDate' parameters are required"
			},
			{ status: 400 }
		)
	}

	try {
		const response = await fetch(
			`${APP_SERVER_URL}/journal/blocks?${queryString}`,
			{
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch blocks")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// POST: Create a new block
export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json()
		const response = await fetch(`${APP_SERVER_URL}/journal/blocks`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(body)
		})
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to create block")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// PUT: Update an existing block
export const PUT = withAuth(async function PUT(request, { authHeader }) {
	const { searchParams } = new URL(request.url)
	const blockId = searchParams.get("blockId")
	if (!blockId) {
		return NextResponse.json(
			{ error: "blockId parameter is required" },
			{ status: 400 }
		)
	}

	try {
		const body = await request.json()
		const response = await fetch(
			`${APP_SERVER_URL}/journal/blocks/${blockId}`,
			{
				method: "PUT",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to update block")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// DELETE: Delete a block
export const DELETE = withAuth(async function DELETE(request, { authHeader }) {
	const { searchParams } = new URL(request.url)
	const blockId = searchParams.get("blockId")
	if (!blockId) {
		return NextResponse.json(
			{ error: "blockId parameter is required" },
			{ status: 400 }
		)
	}

	try {
		const response = await fetch(
			`${APP_SERVER_URL}/journal/blocks/${blockId}`,
			{
				method: "DELETE",
				headers: authHeader
			}
		)
		if (!response.ok) {
			const data = await response.json()
			throw new Error(data.detail || "Failed to delete block")
		}
		return new NextResponse(null, { status: 204 }) // No Content
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
