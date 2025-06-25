import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

const APP_SERVER_URL = process.env.APP_SERVER_URL

// GET: Fetch blocks for a specific date
export async function GET(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const { searchParams } = new URL(request.url)
	const date = searchParams.get("date")
	if (!date) {
		return NextResponse.json(
			{ error: "Date parameter is required" },
			{ status: 400 }
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
		const response = await fetch(
			`${APP_SERVER_URL}/journal/blocks?date=${date}`,
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
}

// POST: Create a new block
export async function POST(request) {
	const session = await auth0.getSession()
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
}

// PUT: Update an existing block
export async function PUT(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const { searchParams } = new URL(request.url)
	const blockId = searchParams.get("blockId")
	if (!blockId) {
		return NextResponse.json(
			{ error: "blockId parameter is required" },
			{ status: 400 }
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
}

// DELETE: Delete a block
export async function DELETE(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const { searchParams } = new URL(request.url)
	const blockId = searchParams.get("blockId")
	if (!blockId) {
		return NextResponse.json(
			{ error: "blockId parameter is required" },
			{ status: 400 }
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
}
