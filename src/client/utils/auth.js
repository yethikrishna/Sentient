/**
 * @file auth.js
 * @description Manages authentication, token storage, and user-specific data related to
 * authorization and application features (like pricing, credits, beta status) for the Electron application.
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
 * - Fetches and stores user-specific data like pricing tier, referral status, beta status, and daily credits
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
	dotenvPath = path.resolve(__dirname, "../../.env") // Relative to this file, up two levels to project root
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
	// Consider whether to throw an error or proceed with defaults if critical env vars are missing.
}

// --- Configuration Variables ---
const auth0Domain = process.env.AUTH0_DOMAIN // Auth0 tenant domain
const clientId = process.env.AUTH0_CLIENT_ID // Auth0 application client ID
const appServerUrl = process.env.APP_SERVER_URL || "http://localhost:5000" // Backend server URL

// --- Keytar Configuration ---
const keytarService = "electron-openid-oauth" // Main service name for Keytar entries
// Keytar Account Names:
// - Refresh token is stored under the OS username. This allows retrieval before the Auth0 user profile (and thus Auth0 user ID) is known,
//   which is crucial for refreshing tokens on app startup if the user was previously logged in.
const keytarAccountRefreshToken = os.userInfo().username
// - Other user-specific data (pricing, credits, beta status, etc.) is stored under an account name
//   prefixed with the Auth0 user ID (e.g., "auth0|12345_pricing"). This requires the user ID to be known.

// --- In-Memory State ---
let accessToken = null // Stores the current Auth0 access token
let profile = null // Stores the decoded ID token, which includes user profile information like 'sub' (Auth0 user ID)
// Note: The refresh token is NOT stored in memory for security reasons. It's only kept encrypted in Keytar.

// --- Getters for In-Memory State ---
/**
 * Retrieves the current access token.
 * @returns {string | null} The current access token, or null if not set.
 */
export function getAccessToken() {
	return accessToken
}

/**
 * Retrieves the current user profile (decoded ID token).
 * @returns {object | null} The user profile object, or null if not set.
 */
export function getProfile() {
	return profile
}

// --- Auth0 URLs ---
/**
 * Constructs the Auth0 authorization URL for initiating the login flow.
 * @returns {string} The full authorization URL.
 * @throws {Error} If Auth0 domain or client ID is not configured.
 */
export function getAuthenticationURL() {
	if (!auth0Domain || !clientId) {
		console.error(
			"[auth.js] Auth0 domain or client ID is missing in environment variables."
		)
		throw new Error("Auth0 domain and/or client ID are not configured.")
	}
	// Scopes: openid (required), profile (user info), offline_access (to get refresh token), email
	// Response type: code (for Authorization Code Grant flow)
	// Redirect URI: Where Auth0 redirects after authentication
	return `https://${auth0Domain}/authorize?scope=openid profile offline_access email&response_type=code&client_id=${clientId}&redirect_uri=http://localhost/callback`
}

/**
 * Constructs the Auth0 logout URL.
 * @returns {string} The full logout URL.
 * @throws {Error} If Auth0 domain or client ID is not configured.
 */
export function getLogOutUrl() {
	if (!auth0Domain || !clientId) {
		console.error(
			"[auth.js] Auth0 domain or client ID is missing for logout URL construction."
		)
		throw new Error(
			"Auth0 domain and/or client ID are not configured for logout."
		)
	}
	// client_id: Identifies the application
	// returnTo: URL to redirect to after logout (optional, configure in Auth0 dashboard)
	return `https://${auth0Domain}/v2/logout?client_id=${clientId}&returnTo=http://localhost/logout`
}

// --- Encryption/Decryption Service Interaction (Backend) ---
/**
 * Encrypts data by sending it to the backend encryption service.
 * @param {string} data The string data to encrypt.
 * @returns {Promise<string>} The encrypted data.
 * @throws {Error} If encryption fails.
 */
async function encrypt(data) {
	try {
		const response = await fetch(`${appServerUrl}/encrypt`, {
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
				"Encryption service response did not contain encrypted_data."
			)
		}
		return result.encrypted_data
	} catch (error) {
		console.error(
			`[auth.js] Error during data encryption via backend: ${error.message}`
		)
		throw error // Re-throw to be handled by caller
	}
}

/**
 * Decrypts data by sending it to the backend decryption service.
 * @param {string} encryptedData The encrypted string data.
 * @returns {Promise<string>} The decrypted data.
 * @throws {Error} If decryption fails.
 */
async function decrypt(encryptedData) {
	try {
		const response = await fetch(`${appServerUrl}/decrypt`, {
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
			// Check specifically for undefined
			throw new Error(
				"Decryption service response did not contain decrypted_data."
			)
		}
		return result.decrypted_data
	} catch (error) {
		console.error(
			`[auth.js] Error during data decryption via backend: ${error.message}`
		)
		throw error // Re-throw
	}
}

// --- Token Management Functions ---

/**
 * Attempts to refresh the access token using a stored refresh token.
 * Updates in-memory `accessToken` and `profile`.
 * If Auth0 provides a new refresh token, it updates the one stored in Keytar.
 * Performs a logout if token refresh fails.
 * @throws {Error} If no refresh token is available, decryption fails, or Auth0 refresh fails.
 */
export async function refreshTokens() {
	console.log("[auth.js] Attempting to refresh authentication tokens...")
	// Retrieve the encrypted refresh token stored under the OS username's Keytar account
	const savedEncryptedRefreshToken = await keytar.getPassword(
		keytarService,
		keytarAccountRefreshToken
	)

	if (!savedEncryptedRefreshToken) {
		console.error(
			`[auth.js] No refresh token found in Keytar for OS user account: '${keytarAccountRefreshToken}'. User needs to log in.`
		)
		await logout() // Clear any potentially inconsistent state from previous sessions
		throw new Error(
			"No refresh token available in Keytar. User needs to log in."
		)
	}

	let decryptedToken
	try {
		console.log("[auth.js] Decrypting stored refresh token...")
		decryptedToken = await decrypt(savedEncryptedRefreshToken)
	} catch (decryptError) {
		console.error(
			"[auth.js] Failed to decrypt the stored refresh token:",
			decryptError.message
		)
		await logout() // Clear the invalid/undecryptable token and session
		throw new Error(
			"Failed to decrypt stored refresh token. Please log in again."
		)
	}

	console.log(
		"[auth.js] Refresh token decrypted. Requesting new access/ID tokens from Auth0..."
	)
	const refreshOptions = {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({
			grant_type: "refresh_token",
			client_id: clientId,
			refresh_token: decryptedToken // Send the decrypted refresh token
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
				"[auth.js] Auth0 token refresh request failed:",
				`Status: ${response.status}`,
				`Error: ${data.error || "Unknown error"}`,
				`Description: ${data.error_description || "No description"}`
			)
			await logout() // Logout user on refresh failure as the session is invalid
			throw new Error(
				`Token refresh failed: ${data.error_description || data.error || response.statusText}`
			)
		}

		if (!data.access_token || !data.id_token) {
			console.error(
				"[auth.js] Auth0 response from token refresh is missing access_token or id_token."
			)
			await logout()
			throw new Error(
				"Incomplete token response received from Auth0 during refresh."
			)
		}

		// Update in-memory state with new tokens
		accessToken = data.access_token
		profile = jwtDecode(data.id_token) // Decode the new ID token to get user profile

		// If Auth0 returns a new refresh token (e.g., due to refresh token rotation),
		// encrypt and update it in Keytar.
		if (data.refresh_token && data.refresh_token !== decryptedToken) {
			console.log(
				"[auth.js] Auth0 returned a new refresh token. Updating it in Keytar..."
			)
			const encryptedNewRefreshToken = await encrypt(data.refresh_token)
			await keytar.setPassword(
				keytarService,
				keytarAccountRefreshToken,
				encryptedNewRefreshToken
			)
			console.log(
				"[auth.js] New refresh token successfully updated in Keytar."
			)
		}

		console.log(
			`[auth.js] Tokens refreshed successfully for user: ${profile?.sub}`
		)
		// Update the general check-in timestamp for the user after successful refresh
		if (profile?.sub) {
			await setCheckinInKeytar(profile.sub)
		}
	} catch (error) {
		console.error(
			"[auth.js] An unexpected error occurred during the token refresh process:",
			error.message
		)
		// Ensure logout on any failure during the try block to maintain a clean state
		if (!error.message.includes("Token refresh failed")) {
			// Avoid double logout if error is already from a failed refresh
			await logout()
		}
		throw error // Re-throw the error to be handled by the caller
	}
}

/**
 * Exchanges an authorization code (obtained from Auth0 callback) for access, ID, and refresh tokens.
 * Stores the new refresh token securely in Keytar.
 * Updates in-memory `accessToken` and `profile`.
 * @param {string} callbackURL The callback URL containing the authorization code.
 * @throws {Error} If the code is missing, token exchange fails, or tokens are incomplete.
 */
export async function loadTokens(callbackURL) {
	console.log(
		"[auth.js] Loading tokens using authorization code from callback URL..."
	)
	const url = new URL(callbackURL)
	const code = url.searchParams.get("code") // Extract authorization code from URL query parameters

	if (!code) {
		console.error(
			"[auth.js] Authorization code not found in the callback URL."
		)
		throw new Error("Authorization code is missing in the callback URL.")
	}

	const params = {
		grant_type: "authorization_code",
		client_id: clientId,
		code: code,
		redirect_uri: "http://localhost/callback" // Must match the redirect URI used in the /authorize request
	}
	const options = {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify(params)
	}

	try {
		console.log(
			"[auth.js] Exchanging authorization code for tokens with Auth0..."
		)
		const response = await fetch(
			`https://${auth0Domain}/oauth/token`,
			options
		)
		const data = await response.json()

		if (!response.ok || data.error) {
			console.error(
				"[auth.js] Auth0 token exchange request failed:",
				`Status: ${response.status}`,
				`Error: ${data.error || "Unknown error"}`,
				`Description: ${data.error_description || "No description"}`
			)
			await logout() // Clear session on failure
			throw new Error(
				`Token exchange failed: ${data.error_description || data.error || response.statusText}`
			)
		}

		// Ensure all required tokens are present in the response
		if (!data.access_token || !data.id_token || !data.refresh_token) {
			console.error(
				"[auth.js] Auth0 response from token exchange is missing one or more required tokens (access, id, or refresh token)."
			)
			await logout()
			throw new Error(
				"Incomplete token response received from Auth0 after initial login."
			)
		}

		// Set in-memory tokens and profile
		accessToken = data.access_token
		profile = jwtDecode(data.id_token)
		const newRefreshToken = data.refresh_token // Temporarily hold the new refresh token

		if (!profile || !profile.sub) {
			console.error(
				"[auth.js] Failed to decode ID token or the 'sub' (user ID) field is missing from the ID token."
			)
			await logout()
			throw new Error(
				"Invalid ID token received from Auth0. User ID could not be determined."
			)
		}
		const userId = profile.sub // Auth0 User ID
		console.log(
			`[auth.js] Tokens loaded successfully via authorization code for user: ${userId}`
		)

		// Encrypt and save the new refresh token to Keytar under the OS username account
		console.log(
			`[auth.js] Encrypting and saving new refresh token to Keytar for OS user account: '${keytarAccountRefreshToken}'...`
		)
		const encryptedNewRefreshToken = await encrypt(newRefreshToken)
		await keytar.setPassword(
			keytarService,
			keytarAccountRefreshToken,
			encryptedNewRefreshToken
		)
		console.log(
			"[auth.js] New refresh token successfully stored in Keytar."
		)

		// Set the initial general check-in timestamp for this user
		await setCheckinInKeytar(userId)
	} catch (error) {
		console.error(
			"[auth.js] An error occurred while loading tokens:",
			error.message
		)
		await logout() // Ensure logout on any failure to maintain a clean state
		throw error // Re-throw to be handled by the caller
	}
}

/**
 * Logs the user out by clearing all session data.
 * Deletes the refresh token from Keytar (associated with OS username).
 * Deletes user-specific data from Keytar if the user ID is known.
 * Resets in-memory `accessToken` and `profile`.
 */
export async function logout() {
	console.log("[auth.js] Performing user logout procedures...")
	const userIdBeforeClear = profile?.sub // Get user ID *before* clearing the profile

	try {
		// Delete the main refresh token (associated with the OS username)
		await keytar.deletePassword(keytarService, keytarAccountRefreshToken)
		console.log(
			`[auth.js] Deleted refresh token from Keytar for OS user account: '${keytarAccountRefreshToken}'.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error deleting refresh token from Keytar for OS user '${keytarAccountRefreshToken}':`,
			error.message
		)
		// Continue with logout even if this fails, to clear other data.
	}

	// If the user ID was available, delete all user-specific Keytar entries
	if (userIdBeforeClear) {
		console.log(
			`[auth.js] Deleting all user-specific Keytar entries for user ID: '${userIdBeforeClear}'...`
		)
		const userSpecificKeySuffixes = [
			"pricing",
			"checkin",
			"referralCode",
			"referrerStatus",
			"betaUserStatus",
			"proCredits",
			"creditsCheckin"
		]
		for (const keySuffix of userSpecificKeySuffixes) {
			const userSpecificAccountName = getUserKeytarAccount(
				userIdBeforeClear,
				keySuffix
			)
			try {
				await keytar.deletePassword(
					keytarService,
					userSpecificAccountName
				)
				// console.log(`[auth.js] Deleted Keytar entry: ${userSpecificAccountName}`);
			} catch (error) {
				console.warn(
					`[auth.js] Warning: Could not delete Keytar entry '${userSpecificAccountName}' during logout (it might not exist):`,
					error.message
				)
			}
		}
		console.log(
			`[auth.js] Finished attempting to delete user-specific Keytar entries for user ID: '${userIdBeforeClear}'.`
		)
	} else {
		console.log(
			"[auth.js] User ID was not available before logout, skipping deletion of user-specific Keytar entries."
		)
	}

	// Reset in-memory authentication state
	accessToken = null
	profile = null
	console.log(
		"[auth.js] In-memory access token and profile have been cleared. Logout complete."
	)
}

// --- User-Specific Data Management with Keytar ---

/**
 * Helper function to generate a Keytar account name for user-specific data.
 * Uses the convention: `userId_keyName`.
 * @param {string} userId The Auth0 user ID ('sub').
 * @param {string} key The specific data key (e.g., "pricing", "proCredits").
 * @returns {string} The generated Keytar account name.
 * @throws {Error} If `userId` is not provided.
 */
function getUserKeytarAccount(userId, key) {
	if (!userId) {
		console.error(
			"[auth.js] Cannot generate user-specific Keytar account name: userId is missing."
		)
		throw new Error(
			"[auth.js] Attempted to generate user Keytar account name without a userId."
		)
	}
	return `${userId}_${key}`
}

/**
 * Sets the general activity check-in timestamp for a user in Keytar.
 * This timestamp is used to determine session inactivity.
 * @param {string} userId The Auth0 user ID.
 */
async function setCheckinInKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Cannot set check-in in Keytar: userId is not provided."
		)
		return
	}
	try {
		const accountName = getUserKeytarAccount(userId, "checkin")
		const currentTimestampSeconds = Math.floor(Date.now() / 1000).toString()
		const encryptedTimestamp = await encrypt(currentTimestampSeconds)
		await keytar.setPassword(keytarService, accountName, encryptedTimestamp)
		console.log(
			`[auth.js] General activity check-in timestamp updated in Keytar for user ${userId}.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting general check-in timestamp in Keytar for user ${userId}:`,
			error.message
		)
	}
}

/**
 * Fetches the user's role (pricing tier) from the backend and stores it encrypted in Keytar.
 * Requires the user to be authenticated (profile and access token must be set).
 * @throws {Error} If user is not authenticated, or if fetching/storing role fails.
 */
export async function fetchAndSetUserRole() {
	if (!profile || !profile.sub) {
		throw new Error(
			"Cannot fetch user role: User profile or user ID ('sub') is not available. Please ensure the user is logged in."
		)
	}
	const userId = profile.sub
	const authHeader = getAccessToken()
		? { Authorization: `Bearer ${getAccessToken()}` }
		: null // Prepare auth header
	if (!authHeader) {
		throw new Error(
			"Cannot fetch user role: Access token is missing. Please ensure the user is logged in."
		)
	}

	console.log(
		`[auth.js] Fetching user role for user ${userId} from backend API...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-role`, {
			method: "POST", // Backend expects POST for this endpoint
			headers: { "Content-Type": "application/json", ...authHeader }
			// Body might not be needed if backend derives user_id from the token.
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Error fetching user role from backend: ${response.statusText}. Details: ${errorText}`
			)
		}
		const { role } = await response.json() // Expects { role: "..." }

		if (role) {
			console.log(
				`[auth.js] User role received from backend: '${role}'. Storing as pricing tier for user ${userId}...`
			)
			const accountName = getUserKeytarAccount(userId, "pricing")
			const encryptedPricingTier = await encrypt(role)
			await keytar.setPassword(
				keytarService,
				accountName,
				encryptedPricingTier
			) // Store under user-specific account
			console.log(
				`[auth.js] Pricing tier ('${role}') stored successfully in Keytar for user ${userId}.`
			)
			// Update general check-in time when role is confirmed/fetched
			await setCheckinInKeytar(userId)
		} else {
			console.warn(
				`[auth.js] No role information was returned from the backend for user ${userId}. Pricing tier not stored.`
			)
		}
	} catch (error) {
		console.error(
			`[auth.js] Error during fetching or setting user role for ${userId}: ${error.message}`
		)
		throw new Error(`Failed to fetch or set user role for ${userId}.`)
	}
}

// --- Keytar Getters/Setters for User-Specific Data ---
// These functions now consistently require `userId` to interact with the correct Keytar entries.

/**
 * Retrieves the pricing tier for a specific user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<string | null>} The decrypted pricing tier, or null if not found or error.
 */
export async function getPricingFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get pricing from Keytar without userId."
		)
		return null
	}
	const accountName = getUserKeytarAccount(userId, "pricing")
	try {
		const encryptedPricing = await keytar.getPassword(
			keytarService,
			accountName
		)
		if (!encryptedPricing) return null // Not found
		return await decrypt(encryptedPricing)
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving pricing tier for user ${userId} from Keytar:`,
			error.message
		)
		return null
	}
}

/**
 * Retrieves the last general activity check-in timestamp for a user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<number | null>} The timestamp (seconds since epoch), or null if not found or error.
 */
export async function getCheckinFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get check-in timestamp from Keytar without userId."
		)
		return null
	}
	const accountName = getUserKeytarAccount(userId, "checkin")
	try {
		const encryptedCheckin = await keytar.getPassword(
			keytarService,
			accountName
		)
		if (!encryptedCheckin) return null
		const checkinTimestampStr = await decrypt(encryptedCheckin)
		return parseInt(checkinTimestampStr, 10) // Convert to number
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving check-in timestamp for user ${userId} from Keytar:`,
			error.message
		)
		return null
	}
}

/**
 * Retrieves the "pro" credits for a user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<number>} The number of credits, defaults to 0 if not found or error.
 */
export async function getCreditsFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get credits from Keytar without userId. Defaulting to 0."
		)
		return 0
	}
	const accountName = getUserKeytarAccount(userId, "proCredits")
	try {
		const encryptedCredits = await keytar.getPassword(
			keytarService,
			accountName
		)
		if (!encryptedCredits) return 0 // Default to 0 if no entry
		const creditsStr = await decrypt(encryptedCredits)
		return parseInt(creditsStr, 10) || 0 // Ensure it's a number, default 0 on parse error
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving pro credits for user ${userId} from Keytar:`,
			error.message
		)
		return 0 // Default to 0 on error
	}
}

/**
 * Retrieves the last daily credits check-in timestamp for a user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<number | null>} Timestamp (seconds since epoch), or null if not found or error.
 */
export async function getCreditsCheckinFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get credits check-in from Keytar without userId."
		)
		return null
	}
	const accountName = getUserKeytarAccount(userId, "creditsCheckin")
	try {
		const encryptedCheckin = await keytar.getPassword(
			keytarService,
			accountName
		)
		if (!encryptedCheckin) return null
		const checkinTimestampStr = await decrypt(encryptedCheckin)
		return parseInt(checkinTimestampStr, 10)
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving credits check-in timestamp for user ${userId} from Keytar:`,
			error.message
		)
		return null
	}
}

/**
 * Sets the "pro" credits for a user in Keytar.
 * @param {string} userId The Auth0 user ID.
 * @param {number} credits The number of credits to set.
 */
export async function setCreditsInKeytar(userId, credits) {
	if (!userId) {
		console.warn(
			"[auth.js] Cannot set credits in Keytar: userId is not provided."
		)
		return
	}
	const accountName = getUserKeytarAccount(userId, "proCredits")
	try {
		const encryptedCredits = await encrypt(credits.toString())
		await keytar.setPassword(keytarService, accountName, encryptedCredits)
		console.log(
			`[auth.js] Pro credits set to ${credits} in Keytar for user ${userId}.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting pro credits in Keytar for user ${userId}:`,
			error.message
		)
	}
}

/**
 * Sets the daily credits check-in timestamp for a user in Keytar (current time).
 * @param {string} userId The Auth0 user ID.
 */
export async function setCreditsCheckinInKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Cannot set credits check-in in Keytar: userId is not provided."
		)
		return
	}
	const accountName = getUserKeytarAccount(userId, "creditsCheckin")
	try {
		const currentTimestampSecondsStr = Math.floor(
			Date.now() / 1000
		).toString()
		const encryptedTimestamp = await encrypt(currentTimestampSecondsStr)
		await keytar.setPassword(keytarService, accountName, encryptedTimestamp)
		console.log(
			`[auth.js] Daily credits check-in timestamp updated in Keytar for user ${userId}.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting credits check-in timestamp in Keytar for user ${userId}:`,
			error.message
		)
	}
}

/**
 * Retrieves the beta user status for a user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<boolean | null>} True if beta user, false otherwise, or null if not set/error.
 */
export async function getBetaUserStatusFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get beta user status from Keytar without userId."
		)
		return null
	}
	const accountName = getUserKeytarAccount(userId, "betaUserStatus")
	try {
		const betaUserStatusStr = await keytar.getPassword(
			keytarService,
			accountName
		)
		// Explicitly check for null because "false" is a valid string that needs to be parsed to boolean.
		if (betaUserStatusStr === null) return null // Status not set
		return betaUserStatusStr === "true" // Convert stored string "true" to boolean true
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving beta user status for user ${userId} from Keytar:`,
			error.message
		)
		return null // Default to null on error
	}
}

/**
 * Sets the beta user status for a user in Keytar.
 * @param {string} userId The Auth0 user ID.
 * @param {boolean} betaUserStatus The beta status to set.
 */
export async function setBetaUserStatusInKeytar(userId, betaUserStatus) {
	if (!userId) {
		console.warn(
			"[auth.js] Cannot set beta user status in Keytar: userId is not provided."
		)
		return
	}
	const accountName = getUserKeytarAccount(userId, "betaUserStatus")
	try {
		// Store boolean as a string "true" or "false" for consistency with retrieval
		await keytar.setPassword(
			keytarService,
			accountName,
			betaUserStatus.toString()
		)
		console.log(
			`[auth.js] Beta user status set to '${betaUserStatus}' in Keytar for user ${userId}.`
		)
	} catch (error) {
		console.error(
			`[auth.js] Error setting beta user status in Keytar for user ${userId}:`,
			error.message
		)
	}
}

// Note: `resetCreditsIfNecessary` logic was moved to `index.js` (`checkUserInfo`)
// as it involves more application-level logic (checking dates, referrer status).

/**
 * Fetches the user's referral code from the backend and stores it in Keytar.
 * Requires user to be authenticated.
 * @returns {Promise<string | null>} The referral code, or null if not found or error.
 * @throws {Error} If not authenticated or backend call fails.
 */
export async function fetchAndSetReferralCode() {
	if (!profile || !profile.sub) {
		throw new Error(
			"Cannot fetch referral code: User profile or user ID ('sub') is not available."
		)
	}
	const userId = profile.sub
	const authHeader = getAccessToken()
		? { Authorization: `Bearer ${getAccessToken()}` }
		: null
	if (!authHeader) {
		throw new Error("Cannot fetch referral code: Access token is missing.")
	}

	console.log(
		`[auth.js] Fetching referral code for user ${userId} from backend API...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-referral-code`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// Body is likely empty if user identified by token.
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Error fetching referral code from backend: ${response.statusText}. Details: ${errorText}`
			)
		}
		const { referralCode } = await response.json()

		if (referralCode) {
			const accountName = getUserKeytarAccount(userId, "referralCode")
			const encryptedReferralCode = await encrypt(referralCode)
			await keytar.setPassword(
				keytarService,
				accountName,
				encryptedReferralCode
			)
			console.log(
				`[auth.js] Referral code ('${referralCode}') stored locally in Keytar for user ${userId}.`
			)
			return referralCode
		} else {
			console.warn(
				`[auth.js] No referral code was returned from the backend for user ${userId}.`
			)
			return null
		}
	} catch (error) {
		console.error(
			`[auth.js] Error during fetching or setting referral code for user ${userId}:`,
			error.message
		)
		throw error // Re-throw
	}
}

/**
 * Fetches the user's referrer status from the backend and stores it in Keytar.
 * (Referrer status indicates if this user has successfully referred someone).
 * Requires user to be authenticated.
 * @returns {Promise<boolean | null>} The referrer status, or null if error.
 * @throws {Error} If not authenticated or backend call fails.
 */
export async function fetchAndSetReferrerStatus() {
	if (!profile || !profile.sub) {
		throw new Error(
			"Cannot fetch referrer status: User profile or user ID ('sub') is not available."
		)
	}
	const userId = profile.sub
	const authHeader = getAccessToken()
		? { Authorization: `Bearer ${getAccessToken()}` }
		: null
	if (!authHeader) {
		throw new Error(
			"Cannot fetch referrer status: Access token is missing."
		)
	}

	console.log(
		`[auth.js] Fetching referrer status for user ${userId} from backend API...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-referrer-status`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// Body likely empty.
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Error fetching referrer status from backend: ${response.statusText}. Details: ${errorText}`
			)
		}
		const { referrerStatus } = await response.json() // Expects a boolean

		const accountName = getUserKeytarAccount(userId, "referrerStatus")
		// Encrypt the boolean as a string ("true" or "false")
		const encryptedReferrerStatus = await encrypt(referrerStatus.toString())
		await keytar.setPassword(
			keytarService,
			accountName,
			encryptedReferrerStatus
		)
		console.log(
			`[auth.js] Referrer status ('${referrerStatus}') stored locally in Keytar for user ${userId}.`
		)
		return referrerStatus
	} catch (error) {
		console.error(
			`[auth.js] Error during fetching or setting referrer status for user ${userId}:`,
			error.message
		)
		throw error // Re-throw
	}
}

/**
 * Fetches the user's beta access status from the backend and stores it in Keytar.
 * Requires user to be authenticated.
 * @returns {Promise<boolean | null>} The beta status, or null if error.
 * @throws {Error} If not authenticated or backend call fails.
 */
export async function fetchAndSetBetaUserStatus() {
	if (!profile || !profile.sub) {
		throw new Error(
			"Cannot fetch beta user status: User profile or user ID ('sub') is not available."
		)
	}
	const userId = profile.sub
	const authHeader = getAccessToken()
		? { Authorization: `Bearer ${getAccessToken()}` }
		: null
	if (!authHeader) {
		throw new Error(
			"Cannot fetch beta user status: Access token is missing."
		)
	}

	console.log(
		`[auth.js] Fetching beta user status for user ${userId} from backend API...`
	)
	try {
		const response = await fetch(`${appServerUrl}/get-beta-user-status`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// Body likely empty.
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(
				`Error fetching beta user status from backend: ${response.statusText}. Details: ${errorText}`
			)
		}
		const { betaUserStatus } = await response.json() // Expects a boolean

		await setBetaUserStatusInKeytar(userId, betaUserStatus) // Uses the dedicated setter which handles string conversion
		console.log(
			`[auth.js] Beta user status ('${betaUserStatus}') stored locally in Keytar for user ${userId}.`
		)
		return betaUserStatus
	} catch (error) {
		console.error(
			`[auth.js] Error during fetching or setting beta user status for user ${userId}:`,
			error.message
		)
		throw error // Re-throw
	}
}

/**
 * Retrieves the referral code for a user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<string | null>} The decrypted referral code, or null if not found or error.
 */
export async function getReferralCodeFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get referral code from Keytar without userId."
		)
		return null
	}
	const accountName = getUserKeytarAccount(userId, "referralCode")
	try {
		const encryptedReferralCode = await keytar.getPassword(
			keytarService,
			accountName
		)
		if (!encryptedReferralCode) return null
		return await decrypt(encryptedReferralCode)
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving referral code for user ${userId} from Keytar:`,
			error.message
		)
		return null
	}
}

/**
 * Retrieves the referrer status for a user from Keytar.
 * @param {string} userId The Auth0 user ID.
 * @returns {Promise<boolean | null>} True if referrer, false otherwise, or null if not set/error.
 */
export async function getReferrerStatusFromKeytar(userId) {
	if (!userId) {
		console.warn(
			"[auth.js] Attempted to get referrer status from Keytar without userId."
		)
		return null
	}
	const accountName = getUserKeytarAccount(userId, "referrerStatus")
	try {
		const encryptedReferrerStatus = await keytar.getPassword(
			keytarService,
			accountName
		)
		if (encryptedReferrerStatus === null) return null // Status not set
		const referrerStatusStr = await decrypt(encryptedReferrerStatus)
		return referrerStatusStr === "true" // Convert "true" string to boolean
	} catch (error) {
		console.error(
			`[auth.js] Error retrieving referrer status for user ${userId} from Keytar:`,
			error.message
		)
		return null
	}
}