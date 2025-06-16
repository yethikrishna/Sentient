import { NextResponse } from "next/server"
import { auth0 } from "@lib/auth0"
import { getBackendAuthHeader } from "@lib/auth0"

export async function POST(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ message: "Not authenticated" },
			{ status: 401 }
		)
	}

	try {
		const {
			input,
			chatId,
			enable_internet,
			enable_weather,
			enable_news,
			enable_maps
		} = await request.json()
		const authHeader = await getBackendAuthHeader()

		// Fetch user pricing/credits to pass to the backend
		const pricingResponse = await fetch(
			`${process.env.APP_SERVER_URL}/api/get-user-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)
		const userData = await pricingResponse.json()
		const pricing = userData?.data?.pricing || "free"
		const credits = userData?.data?.proCredits || 0

		const backendResponse = await fetch(
			`${process.env.APP_SERVER_URL}/chat`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({
					input,
					chatId,
					pricing,
					credits,
					enable_internet,
					enable_weather,
					enable_news,
					enable_maps
				}),
				// IMPORTANT: duplex must be set to 'half' to stream response body in Next.js Edge/Node runtime
				duplex: "half"
			}
		)

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
				"Content-Type": "text/event-stream",
				"Cache-Control": "no-cache",
				Connection: "keep-alive"
			}
		})
	} catch (error) {
		console.error("API Error in /chat/send:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
}
