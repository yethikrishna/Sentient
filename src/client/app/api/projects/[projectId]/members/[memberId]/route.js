// src/client/app/api/projects/[projectId]/members/[memberId]/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// DELETE: Remove a member from a project
export const DELETE = withAuth(async function DELETE(
	request,
	{ params, authHeader }
) {
	const { projectId, memberId } = params
	try {
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}/members/${memberId}`,
			{
				method: "DELETE",
				headers: { ...authHeader }
			}
		)
		if (!response.ok) {
			const data = await response
				.json()
				.catch(() => ({ detail: "Failed to remove member" }))
			throw new Error(data.detail)
		}
		return NextResponse.json({ message: "Member removed successfully." })
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
