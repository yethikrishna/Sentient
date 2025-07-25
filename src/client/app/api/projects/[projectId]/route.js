// src/client/app/api/projects/[projectId]/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET: Get details for a single project
export const GET = withAuth(async function GET(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}`,
			{
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch project details")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// PUT: Update a project
export const PUT = withAuth(async function PUT(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const body = await request.json()
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}`,
			{
				method: "PUT",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to update project")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// DELETE: Delete a project
export const DELETE = withAuth(async function DELETE(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}`,
			{
				method: "DELETE",
				headers: { ...authHeader }
			}
		)
		if (!response.ok) {
			const data = await response
				.json()
				.catch(() => ({ detail: "Failed to delete project" }))
			throw new Error(data.detail)
		}
		return new Response(null, { status: 204 }) // No content on successful delete
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
