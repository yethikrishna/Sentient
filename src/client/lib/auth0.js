import { Auth0Client } from "@auth0/nextjs-auth0/server"

const isSelfHost = process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"

// Initialize the Auth0 client
export const auth0 = isSelfHost
	? null
	: new Auth0Client({
			// Options are loaded from environment variables by default
			// Ensure necessary environment variables are properly set

			// domain: process.env.AUTH0_DOMAIN,
			// clientId: process.env.AUTH0_CLIENT_ID,
			// clientSecret: process.env.AUTH0_CLIENT_SECRET,
			// appBaseUrl: process.env.APP_BASE_URL,
			// secret: process.env.AUTH0_SECRET,
			authorizationParameters: {
				// In v4, the AUTH0_SCOPE and AUTH0_AUDIENCE environment variables are no longer automatically picked up by the SDK.
				// Instead, we need to provide the values explicitly.
				scope: process.env.AUTH0_SCOPE,
				audience: process.env.AUTH0_AUDIENCE
			},
			// Preserve custom claims like roles from the ID token
			async beforeSessionSaved(session, idToken) {
				return session
		},
		})

export async function getBackendAuthHeader() {
	if (isSelfHost) {
		const staticToken = process.env.SELF_HOST_AUTH_TOKEN
		if (!staticToken) {
			console.error("SELF_HOST_AUTH_TOKEN is not set for selfhost mode.")
			return null
		}
		return { Authorization: `Bearer ${staticToken}` }
	}

	try {
		const tokenResult = await auth0.getAccessToken()
		const accessToken = tokenResult?.accessToken || tokenResult?.token

		if (!accessToken) {
			console.error(
				"lib/auth: Cannot create backend auth header, access token is missing."
			)
			return null
		}
		return { Authorization: `Bearer ${accessToken}` }
	} catch (error) {
		console.error("Error getting access token for backend header:", error)
		return null
	}
}
