import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const onboardingData = await request.json()
		// FIX: The request body from the client is already in the correct format { data: ... }.
		// It should not be wrapped again.
		const response = await fetch(
			`${process.env.NEXT_PUBLIC_APP_SERVER_URL}/api/onboarding`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(onboardingData)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.message || "Failed to save onboarding data")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /onboarding:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
})
