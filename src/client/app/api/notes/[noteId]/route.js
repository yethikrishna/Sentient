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
	const { noteId } = params
	try {
		const response = await fetch(`${appServerUrl}/notes/${noteId}`, {
			headers: { ...authHeader }
		})
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch note.")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

export const PUT = withAuth(async function PUT(
	request,
	{ params, authHeader }
) {
	const { noteId } = params
	try {
		const body = await request.json() // { title, content }
		const response = await fetch(`${appServerUrl}/notes/${noteId}`, {
			method: "PUT",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(body)
		})
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to update note.")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

export const DELETE = withAuth(async function DELETE(
	request,
	{ params, authHeader }
) {
	const { noteId } = params
	try {
		const response = await fetch(`${appServerUrl}/notes/${noteId}`, {
			method: "DELETE",
			headers: { ...authHeader }
		})
		if (!response.ok) {
			const data = await response.json().catch(() => ({}))
			throw new Error(
				data.detail ||
					`Failed to delete note. Status: ${response.status}`
			)
		}
		return new Response(null, { status: 204 }) // No Content
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
