import { NextResponse } from "next/server"
import { auth0, getBackendAuthHeader } from "@lib/auth0"

const isSelfHost = process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"

/**
 * A higher-order function to wrap API route handlers with authentication checks.
 * It verifies the user's session and creates the backend auth header.
 * @param {function} handler The API route handler function to wrap. It will receive `(request, { authHeader, userId, ...params })`.
 * @returns {function} The wrapped handler function.
 */
export function withAuth(handler) {
	if (isSelfHost) {
		return async function (request, params) {
			const authHeader = await getBackendAuthHeader()
			if (!authHeader) {
				return NextResponse.json(
					{ error: "Could not create self-host auth header" },
					{ status: 500 }
				)
			}
			// For self-hosting, the user_id is static.
			return handler(request, {
				...params,
				authHeader,
				userId: "self-hosted-user"
			})
		}
	}

	return async function (request, params) {
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

		// Pass auth details to the actual handler
		return handler(request, {
			...params,
			authHeader,
			userId: session.user.sub
		})
	}
}
