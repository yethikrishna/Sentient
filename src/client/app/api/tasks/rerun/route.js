import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const { taskId } = await request.json()
		const response = await fetch(
			`${process.env.NEXT_PUBLIC_APP_SERVER_URL}/agents/rerun-task`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ taskId: taskId })
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.error || "Failed to re-run task")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/rerun:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
