import { BrowserWindow } from "electron"
import path, { dirname } from "path"
import { fileURLToPath } from "url"
import fetch from "node-fetch"
import querystring from "node:querystring" // Using querystring for URL params

// --- Helper functions for Google OAuth in Electron main process ---

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Ensure these are loaded from your .env via main/index.js or directly if this module is used early
const GOOGLE_OAUTH_CLIENT_ID = process.env.GOOGLE_OAUTH_CLIENT_ID
const GOOGLE_OAUTH_CLIENT_SECRET = process.env.GOOGLE_OAUTH_CLIENT_SECRET
const GOOGLE_OAUTH_REDIRECT_URI = process.env.GOOGLE_OAUTH_REDIRECT_URI

const SCOPES_MAP = {
	gmail: ["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.readonly"],
	// Add other services and their scopes here
	// calendar: ["openid", "email", "profile", "https://www.googleapis.com/auth/calendar.readonly"],
}

export function getGoogleAuthURL(serviceName) {
	if (!GOOGLE_OAUTH_CLIENT_ID || !GOOGLE_OAUTH_REDIRECT_URI) {
		console.error("[GoogleAuth] Client ID or Redirect URI not configured for Google OAuth.")
		throw new Error("Google OAuth client configuration missing.")
	}

	const scopes = SCOPES_MAP[serviceName]
	if (!scopes) {
		console.error(`[GoogleAuth] Unknown service name for Google OAuth: ${serviceName}`)
		throw new Error(`Unsupported Google service: ${serviceName}`)
	}

	const params = {
		client_id: GOOGLE_OAUTH_CLIENT_ID,
		redirect_uri: GOOGLE_OAUTH_REDIRECT_URI,
		response_type: "code",
		scope: scopes.join(" "),
		access_type: "offline", // To get a refresh token
		prompt: "consent" // Ensures refresh token is granted, even if user previously authorized
	}

	return `https://accounts.google.com/o/oauth2/v2/auth?${querystring.stringify(params)}`
}

export async function exchangeCodeForTokens(code) {
	if (!GOOGLE_OAUTH_CLIENT_ID || !GOOGLE_OAUTH_CLIENT_SECRET || !GOOGLE_OAUTH_REDIRECT_URI) {
		console.error("[GoogleAuth] Google OAuth client configuration incomplete for token exchange.")
		throw new Error("Google OAuth client configuration missing for token exchange.")
	}

	const tokenUrl = "https://oauth2.googleapis.com/token"
	const params = {
		code: code,
		client_id: GOOGLE_OAUTH_CLIENT_ID,
		client_secret: GOOGLE_OAUTH_CLIENT_SECRET,
		redirect_uri: GOOGLE_OAUTH_REDIRECT_URI,
		grant_type: "authorization_code"
	}

	try {
		const response = await fetch(tokenUrl, {
			method: "POST",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded"
			},
			body: querystring.stringify(params)
		})

		const tokens = await response.json()
		if (!response.ok || tokens.error) {
			console.error("[GoogleAuth] Error exchanging code for tokens:", tokens.error_description || tokens.error || "Unknown error")
			throw new Error(`Failed to exchange code for tokens: ${tokens.error_description || tokens.error || "Unknown error"}`)
		}

		console.log("[GoogleAuth] Tokens received:", {
			access_token: tokens.access_token ? "PRESENT" : "MISSING",
			refresh_token: tokens.refresh_token ? "PRESENT" : "MISSING",
			id_token: tokens.id_token ? "PRESENT" : "MISSING",
			expires_in: tokens.expires_in,
			scope: tokens.scope
		})
		return tokens // Contains access_token, refresh_token, id_token, etc.
	} catch (error) {
		console.error("[GoogleAuth] Exception during token exchange:", error)
		throw error
	}
}

// This function is called from main/index.js after Electron's Auth0 login
// It expects getAuthHeader from main/index.js to provide the Auth0 token
export async function storeGoogleRefreshTokenOnServer(serviceName, refreshToken, getAuth0AuthHeader) {
	const auth0AuthHeader = getAuth0AuthHeader()
	if (!auth0AuthHeader) {
		console.error("[GoogleAuth] Cannot store Google token: Auth0 authentication header missing.")
		throw new Error("User not authenticated with main application.")
	}

	const backendUrl = process.env.APP_SERVER_URL || "http://localhost:5000"
	const storeTokenUrl = `${backendUrl}/auth/google/store_token`

	try {
		const response = await fetch(storeTokenUrl, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				...auth0AuthHeader // Auth0 Bearer token
			},
			body: JSON.stringify({
				service_name: serviceName,
				google_refresh_token: refreshToken
			})
		})

		const responseData = await response.json()
		if (!response.ok) {
			console.error(`[GoogleAuth] Error storing Google refresh token on server (${response.status}):`, responseData.detail || responseData.message || "Unknown server error")
			throw new Error(responseData.detail || responseData.message || `Failed to store Google token on server. Status: ${response.status}`)
		}

		console.log("[GoogleAuth] Google refresh token stored successfully on server:", responseData.message)
		return { success: true, message: responseData.message }
	} catch (error) {
		console.error("[GoogleAuth] Exception storing Google refresh token on server:", error)
		throw error
	}
}

export function createGoogleAuthWindow(authUrl) {
	const googleAuthWindow = new BrowserWindow({
		width: 600,
		height: 700,
		show: false,
		webPreferences: {
			nodeIntegration: false,
			contextIsolation: true,
			// No preload needed if all logic is in main process
		},
		parent: BrowserWindow.getAllWindows().find(win => win.isMainWindow) || undefined, // Optional: make it a child of main window
        modal: true // Optional: make it modal
	})

	googleAuthWindow.loadURL(authUrl)

	googleAuthWindow.once("ready-to-show", () => {
		googleAuthWindow.show()
	})

	return googleAuthWindow
}