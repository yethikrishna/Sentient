// src/client/utils/auth.js
/**
 * @file auth.js
 * @description Manages authentication, token storage, and user-specific data related to
 * authorization and application features (like pricing, credits) for the Electron application.
 * It interacts with Auth0 for authentication, Keytar for secure local storage of tokens and user data,
 * and a backend server for encryption/decryption services and fetching user metadata.
 *
 * Key functionalities:
 * - Provides URLs for Auth0 authentication and logout.
 * - Handles OAuth 2.0 token exchange (authorization code and refresh token flows).
 * - Securely stores refresh tokens and other sensitive user data using Keytar, encrypted via a backend service.
 * - Manages in-memory state for access tokens and user profiles.
 * - Provides getters for accessing the current access token and user profile.
 * - Implements logout functionality, clearing local and in-memory session data.
 * - Fetches and stores user-specific data like pricing tier, referral status, and daily credits
 *   using Keytar, scoped by user ID.
 * - Ensures that user-specific data is stored and retrieved using a consistent `userId_keyName` convention in Keytar.
 */

import { jwtDecode } from "jwt-decode"
import dotenv from "dotenv"
import keytar from "keytar"
import os from "os"
import fetch from "node-fetch"
import path, { dirname } from "path"
import { fileURLToPath } from "url"
import { app } from "electron" // Electron's app module for path utilities

// --- Constants and Path Configurations ---
const isWindows = process.platform === "win32"
const __filename = fileURLToPath(import.meta.url) // Current file's absolute path
const __dirname = dirname(__filename) // Current file's directory name
let dotenvPath // Path to the .env file, differs for dev and packaged app

// Determine .env file path based on application packaging status
if (app.isPackaged) {
	// Production: Packaged application
	dotenvPath = isWindows
		? path.join(process.resourcesPath, ".env") // Windows: .env in resources folder
		: path.join(app.getPath("home"), ".sentient.env") // Linux/macOS: User-specific .env
	console.log(
		`[auth.js] PRODUCTION: Loading .env from packaged path: ${dotenvPath}`
	)
} else {
	// Development: Running from source
	dotenvPath = path.resolve(__dirname, "../../.env")
	console.log(
		`[auth.js] DEVELOPMENT: Loading .env from dev path: ${dotenvPath}`
	)
}

// Load environment variables from the determined .env file
const dotenvResult = dotenv.config({ path: dotenvPath })
if (dotenvResult.error) {
	console.error(
		`[auth.js] ERROR: Failed to load .env file from ${dotenvPath}. Details:`,
		dotenvResult.error
	)
}

// --- Configuration Variables ---
const auth0Domain = process.env.AUTH0_DOMAIN // Auth0 tenant domain
const clientId = process.env.AUTH0_CLIENT_ID // Auth0 application client ID
const appServerUrl = process.env.APP_SERVER_URL || "http://localhost:5000" // Backend server URL
const auth0Audience = process.env.AUTH0_AUDIENCE 

// --- Keytar Configuration ---
const keytarService = "electron-openid-oauth" 
const keytarAccountRefreshToken = os.userInfo().username // For Auth0 refresh token (OS user specific)

// --- In-Memory State ---
let accessToken = null
let profile = null // Decoded ID token

// --- Getters for In-Memory State ---
export function getAccessToken() {
	return accessToken
}

export function getProfile() {
	return profile
}

// --- Auth0 URLs ---
export function getAuthenticationURL() {
	if (!auth0Domain || !clientId) {
		console.error(
			"[auth.js] Auth0 domain or client ID is missing in environment variables."
		)
		throw new Error("Auth0 domain and/or client ID are not configured.")
	}

	if (!auth0Audience) {
		console.error(
			"[auth.js] Auth0 Audience (AUTH0_AUDIENCE) for custom API is missing."
		)
		throw new Error(
			"Auth0 Custom API Audience is not configured. Please set AUTH0_AUDIENCE in your .env file."
		)
	}

	const apiScopes = [
		"openid", "profile", "email", "offline_access",
		"read:chat", "write:chat", "use:elaborator", "read:profile", "write:profile",
		"scrape:linkedin", "scrape:reddit", "scrape:twitter",
		"manage:google_auth", "read:memory", "write:memory",
		"read:tasks", "write:tasks", "read:notifications",
		"read:config", "write:config", 
		// "admin:user_metadata" // Typically not for end-user tokens unless app has admin features for that user
	].join(" ")

	return `https://${auth0Domain}/authorize?audience=${encodeURIComponent(
		auth0Audience
	)}&scope=${encodeURIComponent(
		apiScopes
	)}&response_type=code&client_id=${clientId}&redirect_uri=http://localhost/callback`
}

export function getLogOutUrl() {
	if (!auth0Domain || !clientId) {
		console.error(
			"[auth.js] Auth0 domain or client ID is missing for logout URL."
		)
		throw new Error("Auth0 domain/client ID not configured for logout.")
	}
	return `https://${auth0Domain}/v2/logout?client_id=${clientId}&returnTo=http://localhost/logout`
}

// --- Encryption/Decryption Service Interaction (Backend) ---
async function encrypt(data) {
	try {
		const response = await fetch(`${appServerUrl}/utils/encrypt`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ data })
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Encryption service failed: ${response.statusText}. Details: ${errorText}`
			)
		}
		const result = await response.json()
		if (!result.encrypted_data) {
			throw new Error(
				"Encryption service response missing encrypted_data."
			)
		}
		return result.encrypted_data
	} catch (error) {
		console.error(`[auth.js] Error during encryption: ${error.message}`)
		throw error
	}
}

async function decrypt(encryptedData) {
	try {
		const response = await fetch(`${appServerUrl}/utils/decrypt`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ encrypted_data: encryptedData })
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Decryption service failed: ${response.statusText}. Details: ${errorText}`
			)
		}
		const result = await response.json()
		if (typeof result.decrypted_data === "undefined") {
			throw new Error(
				"Decryption service response missing decrypted_data."
			)
		}
		return result.decrypted_data
	} catch (error) {
		console.error(`[auth.js] Error during decryption: ${error.message}`)
		throw error
	}
}

// --- Token Management Functions ---
export async function refreshTokens() {
	console.log("[auth.js] Attempting to refresh tokens...")

	if (accessToken && profile) {
		try {
			const decodedAccessToken = jwtDecode(accessToken)
			const currentTime = Date.now() / 1000 
			if (decodedAccessToken.exp > currentTime) {
				console.log(
					`[auth.js] Access token for user ${profile.sub} is still valid. Skipping network refresh.`
				)
				if (profile.sub) {
					await setCheckinInKeytar(profile.sub)
				}
				return 
			} else {
				console.log(
					`[auth.js] Access token for user ${profile.sub} has expired. Proceeding with network refresh.`
				)
			}
		} catch (e) {
			console.warn(
				"[auth.js] Error decoding existing access token or token is invalid. Proceeding with network refresh.",
				e
			)
		}
	} else {
		console.log(
			"[auth.js] No existing access token or profile. Proceeding with network refresh."
		)
	}

	const savedEncryptedRefreshToken = await keytar.getPassword(
		keytarService,
		keytarAccountRefreshToken
	)

	if (!savedEncryptedRefreshToken) {
		console.warn(
			"[auth.js] No refresh token in Keytar. User needs to log in."
		)
		await logout() 
		throw new Error("No refresh token available.")
	}

	if (!auth0Audience) {
		console.error("[auth.js] Auth0 Audience missing for refreshTokens.")
		await logout()
		throw new Error(
			"Auth0 Audience configuration missing for token refresh."
		)
	}

	let decryptedToken
	try {
		decryptedToken = await decrypt(savedEncryptedRefreshToken)
	} catch (decryptError) {
		console.error(
			"[auth.js] Failed to decrypt stored refresh token:",
			decryptError.message
		)
		await logout()
		throw new Error("Failed to decrypt refresh token. Please log in again.")
	}

	const refreshOptions = {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({
			grant_type: "refresh_token",
			client_id: clientId,
			refresh_token: decryptedToken,
			audience: auth0Audience
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
				"[auth.js] Auth0 token refresh failed:",
				data.error_description || data.error || response.statusText
			)
			await logout()
			throw new Error(
				`Token refresh failed: ${
					data.error_description || data.error || "Unknown reason"
				}`
			)
		}

		if (!data.access_token || !data.id_token) {
			console.error(
				"[auth.js] Refresh response missing access_token or id_token."
			)
			await logout()
			throw new Error(
				"Incomplete token response from Auth0 during refresh."
			)
		}

		accessToken = data.access_token
		profile = jwtDecode(data.id_token) 
		
		// console.log("[auth.js] Auth0 /oauth/token response (refreshTokens):", JSON.stringify(data, null, 2));
		// console.log("[auth.js] Decoded ID Token PAYLOAD (refreshTokens):", profile);

		if (data.refresh_token && data.refresh_token !== decryptedToken) {
			console.log(
				"[auth.js] Auth0 returned a new refresh token. Updating in Keytar."
			)
			const encryptedNewRefreshToken = await encrypt(data.refresh_token)
			await keytar.setPassword(
				keytarService,
				keytarAccountRefreshToken,
				encryptedNewRefreshToken
			)
		}

		console.log(
			`[auth.js] Tokens refreshed successfully for user: ${profile?.sub}`
		)
		if (profile?.sub) {
			await setCheckinInKeytar(profile.sub)
		}
	} catch (error) {
		console.error(
			"[auth.js] Unexpected error during token refresh:",
			error.message
		)
		if (!error.message.includes("Token refresh failed")) await logout()
		throw error
	}
}

export async function loadTokens(callbackURL) {
	console.log("[auth.js] Loading tokens from authorization code...")
	const url = new URL(callbackURL)
	const code = url.searchParams.get("code")

	if (!code) {
		console.error("[auth.js] Authorization code missing in callback URL.")
		throw new Error("Authorization code missing.")
	}

	if (!auth0Audience) {
		console.error("[auth.js] Auth0 Audience missing for loadTokens.")
		await logout() 
		throw new Error(
			"Auth0 Audience configuration missing for token exchange."
		)
	}

	const params = {
		grant_type: "authorization_code",
		client_id: clientId,
		code: code,
		redirect_uri: "http://localhost/callback", 
		audience: auth0Audience 
	}
	const options = {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify(params)
	}

	try {
		const response = await fetch(
			`https://${auth0Domain}/oauth/token`,
			options
		)
		const data = await response.json()

		if (!response.ok || data.error) {
			console.error(
				"[auth.js] Auth0 token exchange failed:",
				data.error_description || data.error || response.statusText
			)
			await logout()
			throw new Error(
				`Token exchange failed: ${
					data.error_description || data.error || "Unknown reason"
				}`
			)
		}

		if (!data.access_token || !data.id_token || !data.refresh_token) {
			console.error(
				"[auth.js] Token exchange response missing required tokens."
			)
			await logout()
			throw new Error("Incomplete token response from Auth0 after login.")
		}

		accessToken = data.access_token
		profile = jwtDecode(data.id_token)
		const newRefreshToken = data.refresh_token

		// console.log("[auth.js] Auth0 /oauth/token response (loadTokens):", JSON.stringify(data, null, 2));
		// console.log("[auth.js] Decoded ID Token PAYLOAD (loadTokens):", profile);

		if (!profile || !profile.sub) {
			console.error("[auth.js] Invalid ID token or 'sub' missing.")
			await logout()
			throw new Error("Invalid ID token. User ID not determined.")
		}
		const userId = profile.sub
		console.log(`[auth.js] Tokens loaded successfully for user: ${userId}`)

		const encryptedNewRefreshToken = await encrypt(newRefreshToken)
		await keytar.setPassword(
			keytarService,
			keytarAccountRefreshToken,
			encryptedNewRefreshToken
		)
		console.log("[auth.js] New refresh token stored in Keytar.")

		await setCheckinInKeytar(userId)
		
		// MODIFIED: Return the raw refresh token along with other token data
        return {
            accessToken: data.access_token,
            idToken: data.id_token,
            rawRefreshToken: newRefreshToken // Return the raw refresh token
        };

	} catch (error) {
		console.error("[auth.js] Error loading tokens:", error.message)
		await logout()
		throw error
	}
}


export async function logout() {
	console.log("[auth.js] Performing user logout...")
	const userIdBeforeClear = profile?.sub

	try {
		await keytar.deletePassword(keytarService, keytarAccountRefreshToken)
		console.log(
			`[auth.js] Deleted refresh token from Keytar for OS user: '${keytarAccountRefreshToken}'.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error deleting refresh token for OS user '${keytarAccountRefreshToken}':`,
			error.message
		)
	}

	if (userIdBeforeClear) {
		console.log(
			`[auth.js] Deleting Keytar entries for user ID: '${userIdBeforeClear}'...`
		)
		const userSpecificKeySuffixes = [
			"pricing", "checkin", "referralCode", "referrerStatus",
			"proCredits", "creditsCheckin",
			"google_gmail_refresh_token" // Ensure this is cleared if stored by client
		]
		for (const keySuffix of userSpecificKeySuffixes) {
			const accountName = getUserKeytarAccount(
				userIdBeforeClear,
				keySuffix
			)
			try {
				await keytar.deletePassword(keytarService, accountName)
			} catch (err) {
				// console.warn(`[auth.js] Keytar entry '${accountName}' not found for deletion or error: ${err.message}`);
			}
		}
		console.log(
			`[auth.js] Finished deleting user-specific Keytar entries for ${userIdBeforeClear}.`
		)
	} else {
		console.log(
			"[auth.js] User ID not available, skipping user-specific Keytar entry deletion."
		)
	}

	accessToken = null
	profile = null
	console.log("[auth.js] In-memory session cleared. Logout complete.")
}

// --- User-Specific Data Management with Keytar ---
function getUserKeytarAccount(userId, key) {
	if (!userId) {
		console.error(
			"[auth.js] Cannot generate Keytar account name: userId missing."
		)
		throw new Error("Attempted to use Keytar without userId.")
	}
	return `${userId}_${key}`
}

async function setCheckinInKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] Cannot set check-in: userId missing.")
		return
	}
	try {
		const accountName = getUserKeytarAccount(userId, "checkin")
		const ts = Math.floor(Date.now() / 1000).toString()
		const encryptedTs = await encrypt(ts)
		await keytar.setPassword(keytarService, accountName, encryptedTs)
		console.log(`[auth.js] General check-in updated for user ${userId}.`)
	} catch (error) {
		console.error(
			`[auth.js] Error setting check-in for user ${userId}:`,
			error.message
		)
	}
}

export async function fetchAndSetUserRole() {
	if (!profile || !profile.sub) {
		throw new Error(
			"Cannot fetch user role: User not logged in or profile incomplete."
		)
	}
	const userId = profile.sub
	const customClaimNamespace = auth0Audience.endsWith("/")
		? auth0Audience
		: `${auth0Audience}/` 

	let roleFromClaims = profile[`${customClaimNamespace}role`] 

	if (Array.isArray(roleFromClaims)) {
		roleFromClaims = roleFromClaims.length > 0 ? roleFromClaims[0] : null 
	}

	if (roleFromClaims) {
		console.log(
			`[auth.js] User role '${roleFromClaims}' found in token claims for user ${userId}. Storing as pricing tier.`
		)
		const accountName = getUserKeytarAccount(userId, "pricing")
		const encryptedPricingTier = await encrypt(
			roleFromClaims.toString().toLowerCase()
		) 
		await keytar.setPassword(
			keytarService,
			accountName,
			encryptedPricingTier
		)
		console.log(
			`[auth.js] Pricing tier ('${roleFromClaims}') stored from claims for user ${userId}.`
		)
		await setCheckinInKeytar(userId) 
		return 
	} else {
		console.log(
			`[auth.js] Role not found in token claims for user ${userId}. Falling back to backend API /get-role.`
		)
	}

	const token = getAccessToken()
	if (!token) {
		throw new Error(
			"Cannot fetch user role from backend: Access token missing."
		)
	}

	console.log(
		`[auth.js] Fetching user role for ${userId} from backend /get-role...`
	)
	try {
		const response = await fetch(`${appServerUrl}/utils/get-role`, {
			method: "POST", 
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`
			}
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Error fetching role from backend: ${response.statusText}. Details: ${errorText}`
			)
		}
		const { role } = await response.json()

		if (role) {
			console.log(
				`[auth.js] Role '${role}' received from backend. Storing as pricing for ${userId}.`
			)
			const accountName = getUserKeytarAccount(userId, "pricing")
			const encryptedPricingTier = await encrypt(
				role.toString().toLowerCase()
			)
			await keytar.setPassword(
				keytarService,
				accountName,
				encryptedPricingTier
			)
			console.log(
				`[auth.js] Pricing tier ('${role}') stored from backend for user ${userId}.`
			)
			await setCheckinInKeytar(userId)
		} else {
			console.warn(
				`[auth.js] No role returned from backend for ${userId}. Pricing not stored.`
			)
		}
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting role for ${userId} from backend: ${error.message}`
		)
		throw new Error(
			`Failed to fetch/set user role for ${userId} from backend.`
		)
	}
}

export async function getPricingFromKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] getPricing: userId missing.")
		return null
	}
	const accountName = getUserKeytarAccount(userId, "pricing")
	try {
		const encPricing = await keytar.getPassword(keytarService, accountName)
		return encPricing ? await decrypt(encPricing) : null
	} catch (error) {
		console.error(
			`[auth.js] Error getting pricing for ${userId}:`,
			error.message
		)
		return null
	}
}

export async function getCheckinFromKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] getCheckin: userId missing.")
		return null
	}
	const accountName = getUserKeytarAccount(userId, "checkin")
	try {
		const encCheckin = await keytar.getPassword(keytarService, accountName)
		if (!encCheckin) return null
		return parseInt(await decrypt(encCheckin), 10)
	} catch (error) {
		console.error(
			`[auth.js] Error getting checkin for ${userId}:`,
			error.message
		)
		return null
	}
}

export async function getCreditsFromKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] getCredits: userId missing. Defaulting to 0.")
		return 0
	}
	const accountName = getUserKeytarAccount(userId, "proCredits")
	try {
		const encCredits = await keytar.getPassword(keytarService, accountName)
		if (!encCredits) return 0
		return parseInt(await decrypt(encCredits), 10) || 0
	} catch (error) {
		console.error(
			`[auth.js] Error getting credits for ${userId}:`,
			error.message
		)
		return 0
	}
}

export async function getCreditsCheckinFromKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] getCreditsCheckin: userId missing.")
		return null
	}
	const accountName = getUserKeytarAccount(userId, "creditsCheckin")
	try {
		const encCheckin = await keytar.getPassword(keytarService, accountName)
		if (!encCheckin) return null
		return parseInt(await decrypt(encCheckin), 10)
	} catch (error) {
		console.error(
			`[auth.js] Error getting credits checkin for ${userId}:`,
			error.message
		)
		return null
	}
}

export async function setCreditsInKeytar(userId, credits) {
	if (!userId) {
		console.warn("[auth.js] setCredits: userId missing.")
		return
	}
	const accountName = getUserKeytarAccount(userId, "proCredits")
	try {
		const encCredits = await encrypt(credits.toString())
		await keytar.setPassword(keytarService, accountName, encCredits)
		console.log(
			`[auth.js] Pro credits set to ${credits} for user ${userId}.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting credits for user ${userId}:`,
			error.message
		)
	}
}

export async function setCreditsCheckinInKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] setCreditsCheckin: userId missing.")
		return
	}
	const accountName = getUserKeytarAccount(userId, "creditsCheckin")
	try {
		const ts = Math.floor(Date.now() / 1000).toString()
		const encTs = await encrypt(ts)
		await keytar.setPassword(keytarService, accountName, encTs)
		console.log(
			`[auth.js] Daily credits checkin updated for user ${userId}.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting credits checkin for user ${userId}:`,
			error.message
		)
	}
}

export async function fetchAndSetReferralCode() {
	if (!profile || !profile.sub)
		throw new Error("fetchReferralCode: User not logged in.")
	const userId = profile.sub
	const token = getAccessToken()
	if (!token) throw new Error("fetchReferralCode: Access token missing.")

	const customClaimNamespace = auth0Audience.endsWith("/")
		? auth0Audience
		: `${auth0Audience}/`
	const referralCodeClaim = profile[`${customClaimNamespace}referralCode`]
	if (referralCodeClaim) {
		console.log(
			`[auth.js] Referral code '${referralCodeClaim}' from token claim for ${userId}. Storing.`
		)
		const accountName = getUserKeytarAccount(userId, "referralCode")
		const encryptedCode = await encrypt(referralCodeClaim)
		await keytar.setPassword(keytarService, accountName, encryptedCode)
		return referralCodeClaim
	}

	console.log(
		`[auth.js] Fetching referral code for ${userId} from backend /get-referral-code...`
	)
	try {
		const response = await fetch(
			`${appServerUrl}/utils/get-referral-code`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${token}`
				}
			}
		)
		if (!response.ok) {
			 throw new Error(
				`Backend error /get-referral-code: ${response.statusText}`
			)
		}
		const { referralCode } = await response.json()
		if (referralCode) {
			const accountName = getUserKeytarAccount(userId, "referralCode")
			const encryptedCode = await encrypt(referralCode)
			await keytar.setPassword(keytarService, accountName, encryptedCode)
			console.log(
				`[auth.js] Referral code ('${referralCode}') from backend stored for ${userId}.`
			)
			return referralCode
		} else {
			console.warn(
				`[auth.js] No referral code from backend for ${userId}.`
			)
			return null
		}
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting referral code for ${userId}: ${error.message}`
		)
		throw error
	}
}

export async function fetchAndSetReferrerStatus() {
	if (!profile || !profile.sub)
		throw new Error("fetchReferrerStatus: User not logged in.")
	const userId = profile.sub
	const token = getAccessToken()
	if (!token) throw new Error("fetchReferrerStatus: Access token missing.")

	const customClaimNamespace = auth0Audience.endsWith("/")
		? auth0Audience
		: `${auth0Audience}/`
	const referrerStatusClaim = profile[`${customClaimNamespace}referrerStatus`]
	if (typeof referrerStatusClaim === "boolean") {
		console.log(
			`[auth.js] Referrer status '${referrerStatusClaim}' from token claim for ${userId}. Storing.`
		)
		const accountName = getUserKeytarAccount(userId, "referrerStatus")
		const encryptedStatus = await encrypt(referrerStatusClaim.toString())
		await keytar.setPassword(keytarService, accountName, encryptedStatus)
		return referrerStatusClaim
	}

	console.log(
		`[auth.js] Fetching referrer status for ${userId} from backend /get-referrer-status...`
	)
	try {
		const response = await fetch(
			`${appServerUrl}/utils/get-referrer-status`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${token}`
				}
			}
		)
		if (!response.ok) {
			throw new Error(
				`Backend error /get-referrer-status: ${response.statusText}`
			)
		}
		const { referrerStatus } = await response.json() // Expects boolean
		const accountName = getUserKeytarAccount(userId, "referrerStatus")
		const encryptedStatus = await encrypt(referrerStatus.toString())
		await keytar.setPassword(keytarService, accountName, encryptedStatus)
		console.log(
			`[auth.js] Referrer status ('${referrerStatus}') from backend stored for ${userId}.`
		)
		return referrerStatus
	} catch (error) {
		console.error(
			`[auth.js] Error fetching/setting referrer status for ${userId}: ${error.message}`
		)
		throw error
	}
}

export async function getReferralCodeFromKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] getReferralCode: userId missing.")
		return null
	}
	if (profile && profile.sub === userId) {
		const customClaimNamespace = auth0Audience.endsWith("/")
			? auth0Audience
			: `${auth0Audience}/`
		const code = profile[`${customClaimNamespace}referralCode`]
		if (code) return code
	}
	const accountName = getUserKeytarAccount(userId, "referralCode")
	try {
		const encCode = await keytar.getPassword(keytarService, accountName)
		return encCode ? await decrypt(encCode) : null
	} catch (error) {
		console.error(
			`[auth.js] Error getting referral code (Keytar) for ${userId}:`,
			error.message
		)
		return null
	}
}

export async function getReferrerStatusFromKeytar(userId) {
	if (!userId) {
		console.warn("[auth.js] getReferrerStatus: userId missing.")
		return null
	}
	if (profile && profile.sub === userId) {
		const customClaimNamespace = auth0Audience.endsWith("/")
			? auth0Audience
			: `${auth0Audience}/`
		const status = profile[`${customClaimNamespace}referrerStatus`]
		if (typeof status === "boolean") return status
	}
	const accountName = getUserKeytarAccount(userId, "referrerStatus")
	try {
		const encStatus = await keytar.getPassword(keytarService, accountName)
		if (encStatus === null) return null
		return (await decrypt(encStatus)) === "true"
	} catch (error) {
		console.error(
			`[auth.js] Error getting referrer status (Keytar) for ${userId}:`,
			error.message
		)
		return null
	}
}