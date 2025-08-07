import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json() // { taskId, answers: [{ question_id, answer_text }] }
		const response = await fetch(
			`${appServerUrl}/tasks/answer-clarifications`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({
					task_id: body.taskId,
					answers: body.answers
				})
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to submit answers")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /tasks/answer-clarifications:", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
