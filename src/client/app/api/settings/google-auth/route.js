import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

export async function GET() {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ error: "Could not create auth header" },
			{ status: 500 }
		)
	}

	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/api/get-user-data`,
			{
				method: "POST", // This endpoint is a POST to carry the auth header
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		if (!response.ok) {
			throw new Error("Failed to fetch user settings from backend.")
		}

		const data = await response.json()
		const googleAuthMode = data?.data?.googleAuth?.mode || "default"

		return NextResponse.json({ mode: googleAuthMode })
	} catch (error) {
		console.error("API Error in /settings/google-auth (GET):", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
}

export async function POST(request) {
	const session = await auth0.getSession()
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ error: "Not authenticated" },
			{ status: 401 }
		)
	}

	const authHeader = await getBackendAuthHeader()
	if (!authHeader) {
		return NextResponse.json(
			{ error: "Could not create auth header" },
			{ status: 500 }
		)
	}

	try {
		const body = await request.json() // { mode: 'default' | 'custom', credentialsJson?: string }
		if (!["default", "custom"].includes(body.mode)) {
			return NextResponse.json(
				{ error: "Invalid mode specified." },
				{ status: 400 }
			)
		}
		if (body.mode === "custom" && !body.credentialsJson) {
			return NextResponse.json(
				{ error: "Credentials must be provided for custom mode." },
				{ status: 400 }
			)
		}

		const response = await fetch(
			`${process.env.APP_SERVER_URL}/api/settings/google-auth`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(body)
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.detail || "Failed to update Google auth settings."
			)
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /settings/google-auth (POST):", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
}
