import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const onboardingData = await request.json()
		const response = await fetch(`${appServerUrl}/api/onboarding`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(onboardingData)
		})

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
