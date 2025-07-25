// src/client/app/api/projects/[projectId]/members/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// POST: Invite a member to a project
export const POST = withAuth(async function POST(
	request,
	{ params, authHeader }
) {
	const { projectId } = params
	try {
		const body = await request.json()
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}/members`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)
		const data = await response.json()
		if (!response.ok)
			throw new Error(data.detail || "Failed to invite member")
		return NextResponse.json(data, { status: 201 })
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
