// src/client/app/api/settings/integrations/connect/oauth/callback/route.js
import { NextResponse } from "next/server"
import { headers } from "next/headers"

export async function GET(request) {
	const { searchParams } = new URL(request.url)
	const code = searchParams.get("code")
	const state = searchParams.get("state") // This will be 'gdrive', 'gcalendar', etc.
	const error = searchParams.get("error")

	const baseUrl = process.env.APP_BASE_URL
	if (!baseUrl) {
		console.error("APP_BASE_URL environment variable is not set.")
		return new Response("Server configuration error.", { status: 500 })
	}

	// FIX: Use the public-facing APP_BASE_URL for redirection, not the internal request.url.
	// This ensures the browser is redirected to the correct, publicly accessible address.
	const integrationsUrl = new URL("/integrations", baseUrl)

	if (error) {
		// User denied access or an error occurred
		integrationsUrl.searchParams.set(
			"integration_error",
			`Google authorization failed: ${error}`
		)
		return NextResponse.redirect(integrationsUrl)
	}

	if (!code || !state) {
		integrationsUrl.searchParams.set(
			"integration_error",
			"Authorization failed. Missing code or state from Google."
		)
		return NextResponse.redirect(integrationsUrl)
	}

	try {
		const headersList = await headers() // Needs to be awaited
		const cookie = headersList.get("cookie") // Now this is safe to call
		// The browser session (cookie) is automatically forwarded by Next.js server-side fetch,
		// which authenticates the user to our own API proxy.
		const apiResponse = await fetch(
			`${baseUrl}/api/settings/integrations/connect/oauth`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(cookie && { Cookie: cookie }) // Forward the session cookie
				},
				body: JSON.stringify({
					service_name: state,
					code: code,
					redirect_uri: `${baseUrl}/api/settings/integrations/connect/oauth/callback`
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
		integrationsUrl.searchParams.set("integration_success", state)
		return NextResponse.redirect(integrationsUrl)
	} catch (e) {
		console.error("OAuth callback error:", e)
		integrationsUrl.searchParams.set("integration_error", e.message)
		return NextResponse.redirect(integrationsUrl)
	}
}
