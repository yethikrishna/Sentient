// src/client/app/api/projects/[projectId]/context/[itemId]/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// DELETE: Remove a context item
export const DELETE = withAuth(async function DELETE(
	request,
	{ params, authHeader }
) {
	const { projectId, itemId } = params
	try {
		const response = await fetch(
			`${appServerUrl}/api/projects/${projectId}/context/${itemId}`,
			{
				method: "DELETE",
				headers: { ...authHeader }
			}
		)
		if (!response.ok) {
			const data = await response
				.json()
				.catch(() => ({ detail: "Failed to remove context item" }))
			throw new Error(data.detail)
		}
		return new Response(null, { status: 204 })
	} catch (error) {
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
