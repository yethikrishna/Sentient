// src/client/app/api/settings/integrations/connect/oauth/callback/route.js
import { NextResponse } from "next/server"
import { headers } from "next/headers"

export async function GET(request) {
	const { searchParams } = new URL(request.url)
	const code = searchParams.get("code")
	const state = searchParams.get("state") // This will be 'gdrive', 'gcalendar', etc.
	const error = searchParams.get("error")

	const settingsUrl = new URL("/settings", request.url)

	if (error) {
		// User denied access or an error occurred
		settingsUrl.searchParams.set(
			"integration_error",
			`Google authorization failed: ${error}`
		)
		return NextResponse.redirect(settingsUrl)
	}

	if (!code || !state) {
		settingsUrl.searchParams.set(
			"integration_error",
			"Authorization failed. Missing code or state from Google."
		)
		return NextResponse.redirect(settingsUrl)
	}

	try {
		const headersList = await headers() // Needs to be awaited
		const cookie = headersList.get("cookie") // Now this is safe to call
		// The browser session (cookie) is automatically forwarded by Next.js server-side fetch,
		// which authenticates the user to our own API proxy.
		const apiResponse = await fetch(
			"/api/settings/integrations/connect/oauth",
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(cookie && { Cookie: cookie }) // Forward the session cookie
				},
				body: JSON.stringify({
					service_name: state,
					code: code,
					redirect_uri: `${process.env.NEXT_PUBLIC_APP_SERVER_URL}/api/settings/integrations/connect/oauth/callback`
				})
			}
		)

		if (!apiResponse.ok) {
			const errorData = await apiResponse.json()
			throw new Error(
				errorData.error ||
					"Failed to connect integration on the server."
			)
		}

		// Redirect to settings page with success indicator
		settingsUrl.searchParams.set("integration_success", state)
		return NextResponse.redirect(settingsUrl)
	} catch (e) {
		console.error("OAuth callback error:", e)
		settingsUrl.searchParams.set("integration_error", e.message)
		return NextResponse.redirect(settingsUrl)
	}
}
