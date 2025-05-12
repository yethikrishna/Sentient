import { jwtDecode } from "jwt-decode"
import dotenv from "dotenv"
import keytar from "keytar"
import os from "os"
import fetch from "node-fetch"
import path, { dirname } from "path"
import { fileURLToPath } from "url"
import { app } from "electron"

// --- Constants and Paths ---
const isWindows = process.platform === "win32"
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
let dotenvPath

if (app.isPackaged) {
	dotenvPath = isWindows
		? path.join(process.resourcesPath, ".env")
		: path.join(app.getPath("home"), ".sentient.env")
	console.log(`[auth.js] Loading .env from packaged path: ${dotenvPath}`)
} else {
	dotenvPath = path.resolve(__dirname, "../../.env") // Adjust path as needed
	console.log(`[auth.js] Loading .env from dev path: ${dotenvPath}`)
}

dotenv.config({ path: dotenvPath })
if (dotenv.config({ path: dotenvPath }).error) {
	console.error(`[auth.js] ERROR loading .env from ${dotenvPath}`)
}

const auth0Domain = process.env.AUTH0_DOMAIN
const clientId = process.env.AUTH0_CLIENT_ID
const appServerUrl = process.env.APP_SERVER_URL || "http://localhost:5000"
const keytarService = "electron-openid-oauth" // Main service name

// Keytar Account Names:
// Use OS username for the refresh token (allows finding it before user profile is known)
const keytarAccountRefreshToken = os.userInfo().username
// Use Auth0 user ID (sub) for user-specific data (pricing, credits, etc.)
// This means we need the userId to access/set this data.

// --- In-Memory State ---
let accessToken = null
let profile = null // Contains 'sub' which is the userId
// refreshToken is not stored in memory, only encrypted in Keytar

// --- Getters ---
export function getAccessToken() {
	return accessToken
}
export function getProfile() {
	return profile
}

// --- Auth URLs ---
export function getAuthenticationURL() {
	if (!auth0Domain || !clientId)
		throw new Error("Auth0 domain/clientId missing.")
	return `https://${auth0Domain}/authorize?scope=openid profile offline_access email&response_type=code&client_id=${clientId}&redirect_uri=http://localhost/callback`
}
export function getLogOutUrl() {
	if (!auth0Domain || !clientId)
		throw new Error("Auth0 domain/clientId missing.")
	return `https://${auth0Domain}/v2/logout?client_id=${clientId}&returnTo=http://localhost/logout` // Added example returnTo
}

// --- Encryption/Decryption --- (Relies on backend)
async function encrypt(data) {
	try {
		const response = await fetch(`${appServerUrl}/encrypt`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ data })
		})
		if (!response.ok)
			throw new Error(`Encryption failed: ${response.statusText}`)
		const result = await response.json()
		return result.encrypted_data
	} catch (error) {
		console.error(`[auth.js] Error during encryption: ${error}`)
		throw error
	}
}
async function decrypt(encryptedData) {
	try {
		const response = await fetch(`${appServerUrl}/decrypt`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ encrypted_data: encryptedData })
		})
		if (!response.ok)
			throw new Error(`Decryption failed: ${response.statusText}`)
		const result = await response.json()
		return result.decrypted_data
	} catch (error) {
		console.error(`[auth.js] Error during decryption: ${error}`)
		throw error
	}
}

// --- Token Management ---

export async function refreshTokens() {
	console.log("[auth.js] Attempting to refresh tokens...")
	// Get encrypted refresh token stored under the OS username
	const savedEncryptedRefreshToken = await keytar.getPassword(
		keytarService,
		keytarAccountRefreshToken
	)

	if (!savedEncryptedRefreshToken) {
		console.error(
			"[auth.js] No refresh token found in Keytar for account:",
			keytarAccountRefreshToken
		)
		await logout() // Clear any potentially inconsistent state
		throw new Error("No available refresh token.")
	}

	let decryptedToken
	try {
		decryptedToken = await decrypt(savedEncryptedRefreshToken)
	} catch (decryptError) {
		console.error(
			"[auth.js] Failed to decrypt refresh token:",
			decryptError
		)
		await logout() // Clear invalid token
		throw new Error("Failed to decrypt refresh token.")
	}

	console.log(
		"[auth.js] Refresh token decrypted, requesting new tokens from Auth0..."
	)
	const refreshOptions = {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({
			grant_type: "refresh_token",
			client_id: clientId,
			refresh_token: decryptedToken
		})
	}

	try {
		const response = await fetch(
			`https://${auth0Domain}/oauth/token`,
			refreshOptions
		)
		const data = await response.json()

		if (!response.ok || data.error) {
			console.error(
				"[auth.js] Auth0 token refresh error:",
				data.error || response.statusText,
				data.error_description || ""
			)
			await logout() // Logout on refresh failure
			throw new Error(
				`Token refresh failed: ${data.error_description || data.error || response.statusText}`
			)
		}

		if (!data.access_token || !data.id_token) {
			console.error(
				"[auth.js] Auth0 response missing access_token or id_token."
			)
			await logout()
			throw new Error("Incomplete token response from Auth0.")
		}

		accessToken = data.access_token
		profile = jwtDecode(data.id_token) // Update profile (contains userId 'sub')

		// IMPORTANT: If Auth0 returned a NEW refresh token, update it in Keytar
		if (data.refresh_token && data.refresh_token !== decryptedToken) {
			console.log(
				"[auth.js] Auth0 returned a new refresh token. Updating Keytar..."
			)
			const encryptedNewToken = await encrypt(data.refresh_token)
			await keytar.setPassword(
				keytarService,
				keytarAccountRefreshToken,
				encryptedNewToken
			)
		}

		console.log(
			`[auth.js] Tokens refreshed successfully for user: ${profile?.sub}`
		)
		// Update checkin timestamp for the specific user
		if (profile?.sub) {
			await setCheckinInKeytar(profile.sub)
		}
	} catch (error) {
		console.error("[auth.js] Unexpected error during token refresh:", error)
		await logout() // Ensure logout on any failure
		throw error // Re-throw the error
	}
}

export async function loadTokens(callbackURL) {
	console.log("[auth.js] Loading tokens from callback URL...")
	const url = new URL(callbackURL)
	const code = url.searchParams.get("code")
	if (!code) {
		console.error("[auth.js] No authorization code found in callback URL.")
		throw new Error("Authorization code missing in callback URL.")
	}

	const params = {
		grant_type: "authorization_code",
		client_id: clientId,
		code: code,
		redirect_uri: "http://localhost/callback"
	}
	const options = {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify(params)
	}

	try {
		console.log("[auth.js] Exchanging authorization code for tokens...")
		const response = await fetch(
			`https://${auth0Domain}/oauth/token`,
			options
		)
		const data = await response.json()

		if (!response.ok || data.error) {
			console.error(
				"[auth.js] Auth0 token exchange error:",
				data.error || response.statusText,
				data.error_description || ""
			)
			await logout()
			throw new Error(
				`Token exchange failed: ${data.error_description || data.error || response.statusText}`
			)
		}

		if (!data.access_token || !data.id_token || !data.refresh_token) {
			console.error(
				"[auth.js] Auth0 response missing required tokens (access, id, refresh)."
			)
			await logout()
			throw new Error("Incomplete token response from Auth0.")
		}

		accessToken = data.access_token
		profile = jwtDecode(data.id_token)
		const newRefreshToken = data.refresh_token // Keep the refresh token separate temporarily

		if (!profile || !profile.sub) {
			console.error(
				"[auth.js] Failed to decode ID token or 'sub' field missing."
			)
			await logout()
			throw new Error("Invalid ID token received.")
		}
		const userId = profile.sub
		console.log(`[auth.js] Tokens loaded successfully for user: ${userId}`)

		// Encrypt and save refresh token under OS username account
		console.log(
			"[auth.js] Encrypting and saving refresh token to Keytar account:",
			keytarAccountRefreshToken
		)
		const encryptedToken = await encrypt(newRefreshToken)
		await keytar.setPassword(
			keytarService,
			keytarAccountRefreshToken,
			encryptedToken
		)

		// Set initial checkin time for this user
		await setCheckinInKeytar(userId)
	} catch (error) {
		console.error("[auth.js] Error loading tokens:", error)
		await logout() // Ensure logout on failure
		throw error
	}
}

export async function logout() {
	console.log("[auth.js] Performing logout...")
	const userId = profile?.sub // Get userId BEFORE clearing profile

	// Delete the main refresh token (associated with OS user)
	await keytar.deletePassword(keytarService, keytarAccountRefreshToken)
	console.log(
		"[auth.js] Deleted refresh token for account:",
		keytarAccountRefreshToken
	)

	// If we know the user ID, delete user-specific Keytar entries
	if (userId) {
		console.log(
			"[auth.js] Deleting user-specific Keytar entries for:",
			userId
		)
		const userSpecificKeys = [
			"pricing",
			"checkin",
			"referralCode",
			"referrerStatus",
			"betaUserStatus",
			"proCredits",
			"creditsCheckin"
		]
		for (const key of userSpecificKeys) {
			await keytar.deletePassword(keytarService, `${userId}_${key}`) // Use user-specific account name convention
		}
		console.log("[auth.js] User-specific Keytar entries deleted.")
	} else {
		console.log(
			"[auth.js] User ID unknown, skipping deletion of user-specific Keytar entries."
		)
	}

	// Reset in-memory state
	accessToken = null
	profile = null
	// refreshToken variable was never really used after storage, ensure it's null if it was
	// refreshToken = null;
	console.log("[auth.js] In-memory tokens and profile cleared.")
}

// --- User Role and Status Management ---

/** Helper to generate user-specific keytar account name */
function getUserKeytarAccount(userId, key) {
	if (!userId)
		throw new Error(
			"[auth.js] Cannot generate user keytar account: userId is missing."
		)
	return `${userId}_${key}` // Convention: userId_keyName
}

// Sets the GENERAL check-in time (used for inactivity logout)
async function setCheckinInKeytar(userId) {
	if (!userId) return
	try {
		const account = getUserKeytarAccount(userId, "checkin")
		const encryptedDate = await encrypt(
			Math.floor(Date.now() / 1000).toString()
		)
		await keytar.setPassword(keytarService, account, encryptedDate)
		console.log(`[auth.js] Check-in timestamp updated for user ${userId}`)
	} catch (error) {
		console.error(
			`[auth.js] Error setting checkin for user ${userId}:`,
			error
		)
	}
}

export async function fetchAndSetUserRole() {
	// Assumes profile is already set by refreshTokens or loadTokens
	if (!profile || !profile.sub)
		throw new Error("Cannot fetch role: User profile/ID not available.")
	const userId = profile.sub
	const authHeader = getAuthHeader() // Get auth header
	if (!authHeader) throw new Error("Cannot fetch role: Access token missing.")

	console.log(`[auth.js] Fetching role for user ${userId} from backend...`)
	try {
		const response = await fetch(`${appServerUrl}/get-role`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader } // Send auth header
			// Body might not be needed if backend uses token
			// body: JSON.stringify({ user_id: userId })
		})
		if (!response.ok)
			throw new Error(`Error fetching role: ${response.statusText}`)
		const { role } = await response.json()

		if (role) {
			console.log(
				`[auth.js] Role received: ${role}. Storing pricing for user ${userId}...`
			)
			const account = getUserKeytarAccount(userId, "pricing")
			const encryptedPricing = await encrypt(role)
			await keytar.setPassword(keytarService, account, encryptedPricing) // Store under user-specific account
			console.log(
				`[auth.js] Pricing stored successfully for user ${userId}.`
			)
			// Also update checkin time when role is fetched/confirmed
			await setCheckinInKeytar(userId)
		} else {
			console.warn(`[auth.js] No role found for user ${userId}.`)
		}
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting user role for ${userId}: ${error}`
		)
		throw new Error("Failed to fetch or set user role.")
	}
}

// Functions below now REQUIRE userId to access correct Keytar entry

export async function getPricingFromKeytar(userId) {
	if (!userId) return null
	const account = getUserKeytarAccount(userId, "pricing")
	try {
		const encryptedPricing = await keytar.getPassword(
			keytarService,
			account
		)
		if (!encryptedPricing) return null
		return await decrypt(encryptedPricing)
	} catch (error) {
		console.error(
			`[auth.js] Error getting pricing for user ${userId} from keytar: ${error}`
		)
		return null
	}
}

export async function getCheckinFromKeytar(userId) {
	if (!userId) return null
	const account = getUserKeytarAccount(userId, "checkin")
	try {
		const encryptedCheckin = await keytar.getPassword(
			keytarService,
			account
		)
		if (!encryptedCheckin) return null
		const checkin = await decrypt(encryptedCheckin)
		return parseInt(checkin, 10)
	} catch (error) {
		console.error(
			`[auth.js] Error getting checkin for user ${userId} from keytar: ${error}`
		)
		return null
	}
}

export async function getCreditsFromKeytar(userId) {
	if (!userId) return 0 // Default credits if no user
	const account = getUserKeytarAccount(userId, "proCredits")
	try {
		const encryptedCredits = await keytar.getPassword(
			keytarService,
			account
		)
		if (!encryptedCredits) return 0
		const credits = await decrypt(encryptedCredits)
		return parseInt(credits, 10) || 0
	} catch (error) {
		console.error(
			`[auth.js] Error getting credits for user ${userId} from keytar: ${error}`
		)
		return 0
	}
}

export async function getCreditsCheckinFromKeytar(userId) {
	if (!userId) return null
	const account = getUserKeytarAccount(userId, "creditsCheckin")
	try {
		const encryptedCheckin = await keytar.getPassword(
			keytarService,
			account
		)
		if (!encryptedCheckin) return null
		const checkin = await decrypt(encryptedCheckin)
		return parseInt(checkin, 10)
	} catch (error) {
		console.error(
			`[auth.js] Error getting creditsCheckin for user ${userId} from keytar: ${error}`
		)
		return null
	}
}

export async function setCreditsInKeytar(userId, credits) {
	if (!userId) return
	const account = getUserKeytarAccount(userId, "proCredits")
	try {
		const encryptedCredits = await encrypt(credits.toString())
		await keytar.setPassword(keytarService, account, encryptedCredits)
	} catch (error) {
		console.error(
			`[auth.js] Error setting credits for user ${userId} in keytar: ${error}`
		)
	}
}

export async function setCreditsCheckinInKeytar(userId) {
	if (!userId) return
	const account = getUserKeytarAccount(userId, "creditsCheckin")
	try {
		const currentDate = Math.floor(Date.now() / 1000).toString()
		const encryptedDate = await encrypt(currentDate)
		await keytar.setPassword(keytarService, account, encryptedDate)
	} catch (error) {
		console.error(
			`[auth.js] Error setting creditsCheckin for user ${userId} in keytar: ${error}`
		)
	}
}

export async function getBetaUserStatusFromKeytar(userId) {
	if (!userId) return null
	const account = getUserKeytarAccount(userId, "betaUserStatus")
	try {
		const betaUserStatus = await keytar.getPassword(keytarService, account)
		if (betaUserStatus === null) return null // Explicitly check null, as 'false' string is valid
		return betaUserStatus === "true"
	} catch (error) {
		console.error(
			`[auth.js] Error getting betaStatus for user ${userId} from keytar: ${error}`
		)
		return null
	}
}

export async function setBetaUserStatusInKeytar(userId, betaUserStatus) {
	if (!userId) return
	const account = getUserKeytarAccount(userId, "betaUserStatus")
	try {
		await keytar.setPassword(
			keytarService,
			account,
			betaUserStatus.toString()
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting betaStatus for user ${userId} in keytar: ${error}`
		)
	}
}

// resetCreditsIfNecessary is now called with userId in index.js
// export async function resetCreditsIfNecessary(userId) { ... } // Logic moved to index.js checkUserInfo

export async function fetchAndSetReferralCode() {
	if (!profile || !profile.sub)
		throw new Error(
			"Cannot fetch referral code: User profile/ID not available."
		)
	const userId = profile.sub
	const authHeader = getAuthHeader()
	if (!authHeader)
		throw new Error("Cannot fetch referral code: Access token missing.")

	console.log(
		`[auth.js] Fetching referral code for user ${userId} from backend...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-referral-code`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// body: JSON.stringify({ user_id: userId }) // Body likely empty now
		})
		if (!response.ok)
			throw new Error(
				`Error fetching referral code: ${response.statusText}`
			)
		const { referralCode } = await response.json()

		if (referralCode) {
			const account = getUserKeytarAccount(userId, "referralCode")
			const encryptedReferralCode = await encrypt(referralCode)
			await keytar.setPassword(
				keytarService,
				account,
				encryptedReferralCode
			)
			console.log(
				`[auth.js] Referral code stored locally for user ${userId}.`
			)
			return referralCode
		} else {
			console.warn(
				`[auth.js] No referral code returned from backend for user ${userId}.`
			)
			return null
		}
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting referral code for ${userId}: ${error}`
		)
		throw error
	}
}

export async function fetchAndSetReferrerStatus() {
	if (!profile || !profile.sub)
		throw new Error(
			"Cannot fetch referrer status: User profile/ID not available."
		)
	const userId = profile.sub
	const authHeader = getAuthHeader()
	if (!authHeader)
		throw new Error("Cannot fetch referrer status: Access token missing.")

	console.log(
		`[auth.js] Fetching referrer status for user ${userId} from backend...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-referrer-status`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// body: JSON.stringify({ user_id: userId }) // Body likely empty now
		})
		if (!response.ok)
			throw new Error(
				`Error fetching referrer status: ${response.statusText}`
			)
		const { referrerStatus } = await response.json() // Expecting boolean

		const account = getUserKeytarAccount(userId, "referrerStatus")
		const encryptedReferrerStatus = await encrypt(referrerStatus.toString())
		await keytar.setPassword(
			keytarService,
			account,
			encryptedReferrerStatus
		)
		console.log(
			`[auth.js] Referrer status (${referrerStatus}) stored locally for user ${userId}.`
		)
		return referrerStatus
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting referrer status for ${userId}: ${error}`
		)
		throw error
	}
}

export async function fetchAndSetBetaUserStatus() {
	if (!profile || !profile.sub)
		throw new Error(
			"Cannot fetch beta status: User profile/ID not available."
		)
	const userId = profile.sub
	const authHeader = getAuthHeader()
	if (!authHeader)
		throw new Error("Cannot fetch beta status: Access token missing.")

	console.log(
		`[auth.js] Fetching beta status for user ${userId} from backend...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-beta-user-status`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// body: JSON.stringify({ user_id: userId }) // Body likely empty now
		})
		if (!response.ok)
			throw new Error(
				`Error fetching beta status: ${response.statusText}`
			)
		const { betaUserStatus } = await response.json() // Expecting boolean

		await setBetaUserStatusInKeytar(userId, betaUserStatus) // Uses user-specific account
		console.log(
			`[auth.js] Beta status (${betaUserStatus}) stored locally for user ${userId}.`
		)
		return betaUserStatus
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting beta status for ${userId}: ${error}`
		)
		throw error
	}
}

export async function getReferralCodeFromKeytar(userId) {
	if (!userId) return null
	const account = getUserKeytarAccount(userId, "referralCode")
	try {
		const encryptedReferralCode = await keytar.getPassword(
			keytarService,
			account
		)
		if (!encryptedReferralCode) return null
		return await decrypt(encryptedReferralCode)
	} catch (error) {
		console.error(
			`[auth.js] Error getting referral code for user ${userId} from keytar: ${error}`
		)
		return null
	}
}

export async function getReferrerStatusFromKeytar(userId) {
	if (!userId) return null
	const account = getUserKeytarAccount(userId, "referrerStatus")
	try {
		const encryptedReferrerStatus = await keytar.getPassword(
			keytarService,
			account
		)
		if (encryptedReferrerStatus === null) return null
		const referrerStatus = await decrypt(encryptedReferrerStatus)
		return referrerStatus === "true"
	} catch (error) {
		console.error(
			`[auth.js] Error getting referrer status for user ${userId} from keytar: ${error}`
		)
		return null
	}
}