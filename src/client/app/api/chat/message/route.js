import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const {
			messages,
			chatId
		} = await request.json()

		// Fetch user pricing/credits to pass to the backend
		const pricingResponse = await fetch(
			`${appServerUrl}/api/get-user-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const userData = await pricingResponse.json()
		const pricing = userData?.data?.pricing || "free"
		const credits = userData?.data?.proCredits || 0

		const backendResponse = await fetch(`${appServerUrl}/chat/message`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify({
				// Pass `messages` array instead of `input`
				messages,
				chatId,
				pricing, // Note: pricing and credits are still sent for backend logic
				credits
			}),
			// IMPORTANT: duplex must be set to 'half' to stream response body in Next.js Edge/Node runtime
			duplex: "half"
		})

		if (!backendResponse.ok) {
			const errorText = await backendResponse.text()
			let errorMessage
			try {
				const errorJson = JSON.parse(errorText)
				errorMessage =
					errorJson.detail ||
					errorJson.message ||
					"Backend chat endpoint failed"
			} catch (e) {
				errorMessage =
					errorText ||
					`Backend chat endpoint failed with status ${backendResponse.status}`
			}
			throw new Error(errorMessage)
		}

		// Return the streaming response directly to the client
		return new Response(backendResponse.body, {
			status: 200,
			headers: {
				// Use application/x-ndjson for newline-delimited JSON streams
				"Content-Type": "application/x-ndjson",
				"Cache-Control": "no-cache",
				Connection: "keep-alive",
				"X-Accel-Buffering": "no", // Disable buffering on Netlify/Vercel
				"Content-Encoding": "identity"
			}
		})
	} catch (error) {
		console.error("API Error in /chat/message:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
})
