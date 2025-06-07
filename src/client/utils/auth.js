import {
	getSession as getAuth0Session,
	getAccessToken
} from "@auth0/nextjs-auth0"

export async function getSession() {
	const session = await getAuth0Session()
	return session
}

export async function getBackendAuthHeader() {
	try {
		const { accessToken } = await getAccessToken()
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
