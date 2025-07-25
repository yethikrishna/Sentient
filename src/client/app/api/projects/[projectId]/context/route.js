// src/client/app/api/projects/[projectId]/context/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET: List context items for a project
export const GET = withAuth(async function GET(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}/context`,
			{
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch context items")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// POST: Add a context item to a project
export const POST = withAuth(async function POST(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const body = await request.json()
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}/context`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to add context item")
		return NextResponse.json(data, { status: 201 })
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
