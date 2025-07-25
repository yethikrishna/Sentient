// src/client/app/api/projects/[projectId]/tasks/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET: List tasks for a project
export const GET = withAuth(async function GET(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}/tasks`,
			{
				method: "GET",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to fetch project tasks")
		return NextResponse.json(data)
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
