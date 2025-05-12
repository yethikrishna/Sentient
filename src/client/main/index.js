import { app, BrowserWindow, ipcMain, dialog, Notification } from "electron"
import path, { dirname } from "path"
import { fileURLToPath } from "url"
import fetch from "node-fetch"
import {
	getProfile,
	getAccessToken, // Import getter for access token
	refreshTokens,
	getCheckinFromKeytar,
	getPricingFromKeytar,
	getCreditsFromKeytar,
	setCreditsInKeytar,
	getCreditsCheckinFromKeytar,
	setCreditsCheckinInKeytar,
	fetchAndSetUserRole,
	fetchAndSetReferralCode,
	getReferrerStatusFromKeytar,
	fetchAndSetReferrerStatus,
	fetchAndSetBetaUserStatus,
	getReferralCodeFromKeytar,
	getBetaUserStatusFromKeytar,
	setBetaUserStatusInKeytar
} from "../utils/auth.js"
import { getPrivateData } from "../utils/api.js" // Assuming this might also need user context later
import { createAuthWindow, createLogoutWindow } from "./auth.js"
import dotenv from "dotenv"
import pkg from "electron-updater"
const { autoUpdater } = pkg
import serve from "electron-serve"
import WebSocket from "ws"

/**
 * @file Main process file for the Electron application.
 * Handles application lifecycle, window management, inter-process communication (IPC),
 * auto-updates, and server setup/management.
 * MODIFIED: Added user_id passing via verified Access Token to backend calls.
 *           Aligned HTTP methods. Added WebSocket auth. Scoped Keytar data.
 */

// --- Constants and Paths ---
const isWindows = process.platform === "win32"
const isLinux = process.platform === "linux"
let basePath
let dotenvPath
let appOutDir
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

if (app.isPackaged) {
	console.log("Application is running in PRODUCTION mode (packaged).")
	basePath = isWindows
		? path.join(
				app.getPath("home"),
				"AppData",
				"Local",
				"Programs",
				"Sentient"
			)
		: path.join(app.getPath("home"), ".config", "Sentient")
	dotenvPath = isWindows
		? path.join(process.resourcesPath, ".env")
		: path.join(app.getPath("home"), ".sentient.env")
	appOutDir = path.join(__dirname, "../out")
} else {
	console.log("Application is running in DEVELOPMENT mode.")
	dotenvPath = path.resolve(__dirname, "../../.env") // Adjusted path for dev
	appOutDir = path.join(__dirname, "../out")
}

dotenv.config({ path: dotenvPath })

// --- Helper Functions ---

/**
 * Safely retrieves the user ID (Auth0 sub) from the current profile.
 * Logs an error and returns null if the profile or sub is not available.
 * @returns {string | null} The user ID or null.
 */
function getUserIdFromProfile() {
	const userProfile = getProfile()
	if (!userProfile || !userProfile.sub) {
		console.error(
			"Error: Cannot get user ID. User profile or 'sub' field is missing. Is the user logged in?"
		)
		return null
	}
	return userProfile.sub
}

/**
 * Creates the Authorization header object for API requests.
 * Returns null if the access token is not available.
 * @returns {{ Authorization: string } | null} Header object or null.
 */
function getAuthHeader() {
	const token = getAccessToken()
	if (!token) {
		console.error(
			"Error: Cannot create auth header. Access token is missing."
		)
		return null
	}
	return { Authorization: `Bearer ${token}` }
}

// --- WebSocket Connection ---
let ws
let wsAuthenticated = false // Track WebSocket authentication status

function connectWebSocket() {
	if (
		ws &&
		(ws.readyState === WebSocket.OPEN ||
			ws.readyState === WebSocket.CONNECTING)
	) {
		console.log("WebSocket connection already open or connecting.")
		return
	}

	wsAuthenticated = false // Reset auth status on new connection attempt
	console.log("Attempting to establish WebSocket connection...")
	try {
		ws = new WebSocket("ws://localhost:5000/ws")

		ws.onopen = () => {
			console.log(
				"WebSocket connection opened. Attempting authentication..."
			)
			const token = getAccessToken()
			const userId = getUserIdFromProfile() // Get userId for logging context
			if (token) {
				console.log(
					`WebSocket: Sending auth message for user ${userId || "UNKNOWN"}`
				)
				ws.send(JSON.stringify({ type: "auth", token: token }))
			} else {
				console.error(
					"WebSocket: Cannot authenticate - Access token not available."
				)
				ws.close(1008, "Access token unavailable") // Close with policy violation code
			}
		}

		ws.onmessage = (event) => {
			try {
				const messageData = JSON.parse(event.data)
				console.log("WebSocket message received:", messageData.type)

				// Handle Authentication Response First
				if (messageData.type === "auth_success") {
					wsAuthenticated = true
					console.log(
						`WebSocket authenticated successfully for user: ${messageData.user_id}`
					)
					// Optionally fetch initial data or send ready signal to UI
					return
				} else if (messageData.type === "auth_failure") {
					console.error(
						`WebSocket authentication failed: ${messageData.message}`
					)
					wsAuthenticated = false
					ws.close(1008, "Authentication failed")
					// Optionally notify UI of auth failure
					return
				}

				// Ignore messages if not authenticated (optional, depends on security needs)
				// if (!wsAuthenticated) {
				//     console.warn("WebSocket: Ignoring message - connection not authenticated.");
				//     return;
				// }

				// Process other message types (Notifications)
				let notificationTitle = ""
				let notificationBody = ""

				switch (messageData.type) {
					case "task_completed":
						notificationTitle = "Task Completed!"
						notificationBody = `Task "${messageData.description}" completed successfully.`
						break
					case "task_error":
						notificationTitle = "Task Error!"
						notificationBody = `Task "${messageData.description}" failed: ${messageData.error}`
						break
					case "memory_operation_completed":
						notificationTitle = "Memory Operation Completed!"
						notificationBody = `Memory operation (ID: ${messageData.operation_id}) successful.`
						break
					case "memory_operation_error":
						notificationTitle = "Memory Operation Error!"
						notificationBody = `Memory operation (ID: ${messageData.operation_id}) failed: ${messageData.error}`
						break
					case "task_approval_pending":
						notificationTitle = "Task Approval Needed"
						notificationBody = `Task "${messageData.description}" requires your approval.`
						break
					case "task_cancelled":
						notificationTitle = "Task Cancelled"
						notificationBody = `Task "${messageData.description}" was cancelled: ${messageData.error}`
						break
					case "new_message": // Example: If backend pushes new messages
						notificationTitle = "New Message!"
						notificationBody =
							messageData.message?.substring(0, 100) + "..."
						break
					// Add other notification types here
					default:
						console.log(
							"Ignoring unknown WebSocket message type:",
							messageData.type
						)
				}

				if (notificationTitle && notificationBody) {
					new Notification({
						title: notificationTitle,
						body: notificationBody
					}).show()
				}
			} catch (e) {
				console.error(
					"Error processing WebSocket message:",
					e,
					"Raw data:",
					event.data
				)
			}
		}

		ws.onclose = (event) => {
			wsAuthenticated = false
			console.log(
				`WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`
			)
			// Implement reconnection logic if desired (e.g., exponential backoff)
			// setTimeout(connectWebSocket, 5000); // Simple retry after 5s
		}

		ws.onerror = (error) => {
			wsAuthenticated = false
			console.error("WebSocket error:", error?.message || error)
			// Consider triggering reconnection logic here too
		}
	} catch (e) {
		console.error("Failed to establish WebSocket connection:", e)
		// setTimeout(connectWebSocket, 5000); // Retry on initial connection error
	}
}

// Initial WebSocket connection attempt (will be retried on failure/close if implemented)
// connectWebSocket(); // Connect WebSocket after app is ready and user might be logged in? Moved to startApp

// --- Main Window Management ---
let mainWindow
const appServe = app.isPackaged ? serve({ directory: appOutDir }) : null

export const createAppWindow = () => {
	mainWindow = new BrowserWindow({
		width: 2000,
		height: 1500,
		webPreferences: {
			preload: path.join(__dirname, "preload.js"),
			contextIsolation: true,
			enableRemoteModule: false,
			devTools: !app.isPackaged
		},
		backgroundColor: "#000000",
		autoHideMenuBar: true
	})

	mainWindow.isMainWindow = true // Mark as main window

	if (app.isPackaged) {
		appServe(mainWindow)
			.then(() => mainWindow.loadURL("app://-"))
			.catch((err) => console.error("Failed to serve packaged app:", err))
	} else {
		const devUrl = process.env.ELECTRON_APP_URL || "http://localhost:3000"
		console.log(`Attempting to load URL: ${devUrl}`)
		mainWindow
			.loadURL(devUrl)
			.then(() => {
				console.log("Main window URL loaded.")
				// Attempt WebSocket connection AFTER window loads and auth might be ready
				connectWebSocket()
			})
			.catch((err) => console.error(`Failed to load URL ${devUrl}:`, err))
		mainWindow.webContents.openDevTools()
		mainWindow.webContents.on(
			"did-fail-load",
			(event, errorCode, errorDescription, validatedURL) => {
				console.error(
					`Failed to load ${validatedURL}: ${errorDescription} (Code: ${errorCode})`
				)
			}
		)
	}

	// Close Confirmation Logic... (remains the same as previous version)
	let isExiting = false
	mainWindow.on("close", async (event) => {
		if (!mainWindow?.isMainWindow) {
			return
		} // Skip if not main window
		if (!isExiting) {
			event.preventDefault()
			isExiting = true
			try {
				const response = await dialog.showMessageBox(mainWindow, {
					type: "question",
					buttons: ["Yes", "No"],
					defaultId: 1,
					title: "Confirm Exit",
					message: "Are you sure you want to quit?"
				})
				if (response.response === 0) {
					console.log("User confirmed exit.")
					await dialog.showMessageBox(mainWindow, {
						type: "info",
						message: "Bye friend...",
						title: "Quitting Sentient (click ok to exit)"
					})
					mainWindow.isMainWindow = false // Mark before quitting
					setTimeout(() => app.quit(), 500)
				} else {
					console.log("User cancelled exit.")
					isExiting = false
				}
			} catch (error) {
				console.error("Error during exit confirmation:", error)
				dialog.showErrorBox(
					"Exit Error",
					`An error occurred during shutdown: ${error.message}.`
				)
				isExiting = false
			}
		}
	})

	mainWindow.on("closed", () => {
		if (mainWindow?.isMainWindow) {
			// Only nullify if it was the main window being closed
			mainWindow = null
			if (ws && ws.readyState === WebSocket.OPEN) {
				console.log(
					"Closing WebSocket connection on main window close."
				)
				ws.close()
			}
		}
	})
}

// --- Validity and Status Checks (Production Only) ---

// Updated to use userId from validated token via getUserIdFromProfile
const checkUserInfo = async () => {
	if (!app.isPackaged) return
	console.log("PROD MODE: Performing User Info checks...")

	const userId = getUserIdFromProfile()
	if (!userId) throw new Error("User ID not available for user info checks.") // Should be caught by checkAuthStatus first

	console.log(`PROD MODE: Performing checks for user: ${userId}`)
	try {
		// Pass userId to functions that interact with Keytar user-specific data
		await checkPricingStatus(userId)
		await checkReferralCodeAndStatus(userId)
		await checkBetaUserStatus(userId)
		await resetCreditsIfNecessary(userId)
		await checkGoogleCredentials(userId) // Assuming this needs userId for backend check
		console.log(`PROD MODE: User info checks passed for ${userId}.`)
	} catch (error) {
		console.error(
			`PROD MODE: Error during user info check for ${userId}: ${error.message}. Triggering logout.`
		)
		BrowserWindow.getAllWindows().forEach((win) => {
			if (!win.isLogoutWindow) win.close()
		})
		createLogoutWindow()
		throw error
	}
}

export const checkValidity = async () => {
	if (!app.isPackaged) return
	console.log("PROD MODE: Performing Validity checks...")
	try {
		await checkAuthStatus() // Ensures profile and access token are fresh
		await checkUserInfo() // Uses the profile info (userId) set by checkAuthStatus
		console.log("PROD MODE: Validity checks passed.")
	} catch (error) {
		console.error(
			`PROD MODE: Validity check failed: ${error.message}. Redirecting to Auth window.`
		)
		BrowserWindow.getAllWindows().forEach((win) => {
			if (!win.isAuthWindow && !win.isLogoutWindow) win.close()
		})
		createAuthWindow()
		throw error
	}
}

const checkAuthStatus = async () => {
	// No app.isPackaged check needed here as it's called by checkValidity
	console.log(
		"PROD MODE: Checking authentication status via refreshTokens..."
	)
	try {
		await refreshTokens() // Refreshes token AND sets profile/accessToken globally
		const userProfile = getProfile()
		const token = getAccessToken()
		if (!userProfile || !userProfile.sub || !token) {
			throw new Error(
				"Token refresh succeeded but profile/userId/token is missing."
			)
		}
		console.log(
			`PROD MODE: User authenticated (ID: ${userProfile.sub}). Access token refreshed.`
		)
	} catch (error) {
		console.error(
			`PROD MODE: Authentication check failed: ${error.message}`
		)
		throw new Error("User is not authenticated.")
	}
}

// Status check functions updated to receive and use userId for Keytar operations
// (Implementation details moved to auth.js where Keytar logic resides)

const checkReferralCodeAndStatus = async (userId) => {
	console.log(
		`PROD MODE: Checking Referral Code/Status for user ${userId}...`
	)
	try {
		// Use userId to fetch correct Keytar data
		let referralCode = await getReferralCodeFromKeytar(userId)
		if (!referralCode) {
			console.log(
				"PROD MODE: Referral code not found locally, fetching from server..."
			)
			referralCode = await fetchAndSetReferralCode() // Sets locally for userId
		}
		let referrerStatus = await getReferrerStatusFromKeytar(userId)
		if (referrerStatus === null) {
			console.log(
				"PROD MODE: Referrer status not found locally, fetching from server..."
			)
			referrerStatus = await fetchAndSetReferrerStatus() // Sets locally for userId
		}
		console.log("PROD MODE: Referral code/status check complete.")
	} catch (error) {
		console.error(
			`PROD MODE: Error checking referral code/status for ${userId}: ${error.message}`
		)
		throw new Error("Referral code/status check failed.")
	}
}

const checkBetaUserStatus = async (userId) => {
	console.log(`PROD MODE: Checking Beta User Status for user ${userId}...`)
	try {
		// Use userId for Keytar
		let betaUserStatus = await getBetaUserStatusFromKeytar(userId)
		if (betaUserStatus === null) {
			console.log(
				"PROD MODE: Beta status not found locally, fetching from server..."
			)
			betaUserStatus = await fetchAndSetBetaUserStatus() // Sets locally for userId
		}
		console.log("PROD MODE: Beta user status check complete.")
	} catch (error) {
		console.error(
			`PROD MODE: Error checking beta status for ${userId}: ${error.message}`
		)
		throw new Error("Beta user status check failed.")
	}
}

const checkPricingStatus = async (userId) => {
	console.log(
		`PROD MODE: Checking Pricing Status/Activity for user ${userId}...`
	)
	try {
		// Use userId for Keytar
		const pricing = await getPricingFromKeytar(userId)
		const lastCheckin = await getCheckinFromKeytar(userId)

		if (!pricing || !lastCheckin) {
			console.warn(
				"PROD MODE: Pricing/checkin not found locally. Fetching from server..."
			)
			await fetchAndSetUserRole() // Fetches role based on profile.sub, sets locally for userId
			return // Check again next time
		}

		const currentTimestamp = Math.floor(Date.now() / 1000)
		const sevenDaysInSeconds = 7 * 24 * 60 * 60
		if (currentTimestamp - lastCheckin >= sevenDaysInSeconds) {
			console.warn(
				`PROD MODE: User session expired due to inactivity for ${userId}. Triggering logout.`
			)
			throw new Error("User session expired due to inactivity.")
		}
		console.log("PROD MODE: Pricing status/activity check complete.")
	} catch (error) {
		console.error(
			`PROD MODE: Error checking pricing/session for ${userId}: ${error.message}`
		)
		throw error.message.includes("inactivity")
			? error
			: new Error("Pricing status check failed.")
	}
}

const resetCreditsIfNecessary = async (userId) => {
	console.log(`PROD MODE: Checking Pro Credits reset for user ${userId}...`)
	try {
		// Use userId for Keytar
		const currentDate = new Date().toDateString()
		const checkinTimestamp = await getCreditsCheckinFromKeytar(userId)
		const checkinDate = checkinTimestamp
			? new Date(checkinTimestamp * 1000).toDateString()
			: null

		if (checkinDate !== currentDate) {
			console.log(`PROD MODE: Resetting proCredits for ${userId}.`)
			const referrer = await getReferrerStatusFromKeytar(userId) // Check user's own referrer status
			const creditsToSet = referrer === true ? 10 : 5
			await setCreditsInKeytar(userId, creditsToSet) // Set for user
			await setCreditsCheckinInKeytar(userId) // Set checkin for user
			console.log(
				`PROD MODE: proCredits reset to ${creditsToSet} for ${userId}.`
			)
		} else {
			console.log(
				`PROD MODE: Pro Credits already checked/reset today for ${userId}.`
			)
		}
	} catch (error) {
		console.error(
			`PROD MODE: Error resetting proCredits for ${userId}: ${error.message}`
		)
		throw new Error("Error checking/resetting proCredits")
	}
}

const checkGoogleCredentials = async (userId) => {
	console.log(
		`PROD MODE: Checking Google Credentials via server for user ${userId}...`
	)
	const authHeader = getAuthHeader()
	if (!authHeader)
		throw new Error(
			"Cannot check Google credentials: Access token missing."
		)

	try {
		const googleAuthCheckUrl = `${process.env.APP_SERVER_URL || "http://127.0.0.1:5000"}/authenticate-google`
		const response = await fetch(googleAuthCheckUrl, {
			method: "POST", // POST now, user implicitly identified by token
			headers: { "Content-Type": "application/json", ...authHeader } // Send Auth header
			// Body might not be needed if backend gets user_id from token
			// body: JSON.stringify({ user_id: userId })
		})

		if (!response.ok) {
			let errorDetails = `Server responded with status ${response.status}`
			try {
				const data = await response.json()
				errorDetails = data.error || data.detail || errorDetails
			} catch (e) {}
			throw new Error(`Google credentials check failed: ${errorDetails}`)
		}
		const data = await response.json()
		if (data.success) {
			console.log(
				`PROD MODE: Google credentials check successful for user ${userId}.`
			)
		} else {
			throw new Error(
				data.error ||
					`Google credentials check indicated failure for user ${userId}.`
			)
		}
	} catch (error) {
		console.error(
			`PROD MODE: Error checking Google credentials for ${userId}: ${error.message}`
		)
		throw new Error("Error checking Google credentials")
	}
}

// --- Single Instance Lock --- (Remains the same)
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
	app.quit()
} else {
	app.on("second-instance", () => {
		if (mainWindow) {
			if (mainWindow.isMinimized()) mainWindow.restore()
			mainWindow.focus()
		}
	})
}

// --- Auto Update Logic ---
const checkForUpdates = async () => {
	if (!app.isPackaged) return
	console.log(
		"PROD MODE: Configuring and checking for application updates..."
	)
	let isBetaUser = false
	const userId = getUserIdFromProfile() // Need userId to check correct Keytar entry

	try {
		// Check beta status specifically for the logged-in user
		isBetaUser = userId
			? (await getBetaUserStatusFromKeytar(userId)) || false
			: false
		console.log(
			`PROD MODE: Update check: User ${userId || "N/A"} is ${isBetaUser ? "beta" : "stable"} (local Keytar).`
		)
	} catch (error) {
		console.error(
			"PROD MODE: Failed to get beta status for update check, defaulting to stable.",
			error
		)
	}

	const feedOptions = {
		provider: "github",
		owner: "existence-master",
		repo: "Sentient"
	}
	autoUpdater.setFeedURL(feedOptions)
	autoUpdater.allowPrerelease = isBetaUser
	autoUpdater.channel = isBetaUser ? "beta" : "latest" // Set channel explicitly

	createAppWindow() // Create window FIRST

	try {
		console.log(
			`PROD MODE: Initiating update check for ${autoUpdater.channel} channel...`
		)
		await autoUpdater.checkForUpdatesAndNotify()
	} catch (error) {
		console.error("PROD MODE: Error during update check:", error.message)
	}
}

// --- Application Start Logic ---
const startApp = async () => {
	if (app.isPackaged) {
		console.log("PRODUCTION MODE: Starting application flow.")
		// Check for updates *before* validity checks. Creates window.
		// Uses potentially stale local beta status for channel, but validity check will correct if needed.
		await checkForUpdates()

		const validityCheckDelay = 5000 // 5 seconds
		console.log(
			`PRODUCTION MODE: Scheduling validity checks in ${validityCheckDelay}ms.`
		)
		setTimeout(async () => {
			if (process.env.UPDATING !== "true") {
				console.log(
					"PRODUCTION MODE: Performing scheduled validity checks..."
				)
				try {
					await checkValidity() // Performs auth, gets userId, checks status with server/Keytar
					console.log(
						"PRODUCTION MODE: Validity checks completed successfully."
					)
					// Now that validity is checked and user is likely authed, connect WebSocket
					// connectWebSocket(); // Moved to createAppWindow load finish
				} catch (error) {
					console.error(
						"PRODUCTION MODE: Validity check sequence failed.",
						error.message
					)
					// Error handling (like showing auth window) is done within checkValidity
				}
			} else {
				console.log(
					"PRODUCTION MODE: Skipping validity check due to update in progress."
				)
			}
		}, validityCheckDelay)
	} else {
		// Development Environment
		console.log(
			"DEVELOPMENT MODE: Starting application flow (skipping updates/validity checks)."
		)
		createAppWindow() // Creates window, loads URL, connects WebSocket on load
		mainWindow?.webContents.on("did-finish-load", () => {
			console.log("DEVELOPMENT MODE: Main window finished loading.")
		})
	}
}

// --- App Lifecycle Events ---
app.on("ready", startApp)
app.on("window-all-closed", () => {
	if (process.platform !== "darwin") app.quit()
})
app.on("activate", () => {
	if (BrowserWindow.getAllWindows().length === 0) startApp()
})

// --- AutoUpdater Event Listeners --- (Remain the same, logging only)
if (app.isPackaged) {
	autoUpdater.on("update-available", (info) => {
		console.log("PROD MODE: Update available:", info)
		process.env.UPDATING = "true"
		mainWindow?.webContents.send("update-available", info)
	})
	autoUpdater.on("update-not-available", (info) => {
		console.log("PROD MODE: Update not available:", info)
	})
	autoUpdater.on("error", (err) => {
		console.error("PROD MODE: Error in auto-updater:", err.message)
		process.env.UPDATING = "false"
		mainWindow?.webContents.send("update-error", err.message)
		mainWindow?.webContents.send("update-progress", {
			percent: 0,
			error: true
		})
	})
	autoUpdater.on("download-progress", (progressObj) => {
		console.log(`PROD MODE: Download progress: ${progressObj.percent}%`)
		mainWindow?.webContents.send("update-progress", progressObj)
	})
	autoUpdater.on("update-downloaded", (info) => {
		console.log("PROD MODE: Update downloaded:", info)
		process.env.UPDATING = "false"
		mainWindow?.webContents.send("update-downloaded", info)
	})
}

// --- IPC Handlers ---

// Restart App (AutoUpdate)
ipcMain.on("restart-app", () => {
	if (app.isPackaged) autoUpdater.quitAndInstall()
})

// Get Profile
ipcMain.handle("get-profile", async () => {
	// Returns profile for the currently authenticated user via auth.js
	try {
		const userProfile = getProfile()
		if (!app.isPackaged && !userProfile) {
			return {
				sub: "dev-user-123",
				given_name: "Dev User",
				picture: null
			} // Mock data
		}
		if (!userProfile) return null // Not logged in
		return userProfile
	} catch (error) {
		console.error("Error handling get-profile:", error)
		return null
	}
})

// Get Private Data (Placeholder - Requires specific implementation)
ipcMain.handle("get-private-data", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	if (!app.isPackaged)
		return { mockData: `some dev private data for ${userId}` }

	try {
		console.log(`PROD MODE: Handling get-private-data for user: ${userId}`)
		// Assuming getPrivateData needs modification or its backend target does
		return await getPrivateData(/* pass userId or header if needed */)
	} catch (error) {
		console.error(`Error getting private data for user ${userId}:`, error)
		return { error: error.message, status: 500 }
	}
})

// Get Local Beta Status
ipcMain.handle("get-beta-user-status-local", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) return null // Need ID in prod

	try {
		if (!app.isPackaged) return true // Dev mock
		const betaUserStatus = await getBetaUserStatusFromKeytar(userId) // Pass userId
		return betaUserStatus
	} catch (error) {
		console.error(
			`Error fetching local beta user status for ${userId}: ${error}`
		)
		return null
	}
})

// Log Out
ipcMain.on("log-out", () => {
	console.log("Log-out command received.")
	if (ws && ws.readyState === WebSocket.OPEN) {
		console.log("Closing WebSocket connection on logout.")
		ws.close()
	}
	BrowserWindow.getAllWindows().forEach((win) => {
		if (!win.isLogoutWindow && !win.isAuthWindow) win.close()
	})
	createLogoutWindow() // Handles token clearing etc.
})

// Fetch Local Pricing Plan
ipcMain.handle("fetch-pricing-plan", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) return "free" // Default if no user in prod

	if (!app.isPackaged) return "pro" // Dev mock

	try {
		const pricing = await getPricingFromKeytar(userId) // Pass userId
		console.log(
			`PROD MODE: Fetched local pricing plan for ${userId}:`,
			pricing
		)
		return pricing || "free"
	} catch (error) {
		console.error(
			`PROD MODE: Error fetching local pricing plan for ${userId}: ${error}`
		)
		return "free"
	}
})

// Fetch Local Pro Credits
ipcMain.handle("fetch-pro-credits", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) return 0 // Default if no user in prod

	if (!app.isPackaged) return 999 // Dev mock

	try {
		const credits = await getCreditsFromKeytar(userId) // Pass userId
		console.log(
			`PROD MODE: Fetched local pro credits for ${userId}:`,
			credits
		)
		return credits
	} catch (error) {
		console.error(
			`PROD MODE: Error fetching local pro credits for ${userId}: ${error}`
		)
		return 0
	}
})

// Decrement Local Pro Credits
ipcMain.handle("decrement-pro-credits", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) {
		console.error("PROD MODE: Cannot decrement credits - User ID missing.")
		return false
	}

	if (!app.isPackaged) return true // Dev simulation

	try {
		let credits = await getCreditsFromKeytar(userId) // Pass userId
		credits = Math.max(0, credits - 1)
		await setCreditsInKeytar(userId, credits) // Pass userId
		console.log(
			`PROD MODE: Decremented local pro credits to ${credits} for ${userId}.`
		)
		return true
	} catch (error) {
		console.error(
			`PROD MODE: Error decrementing local pro credits for ${userId}: ${error}`
		)
		return false
	}
})

// Fetch Local Referral Code
ipcMain.handle("fetch-referral-code", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) return null

	if (!app.isPackaged) return "DEVREFERRAL" // Dev mock

	try {
		const referralCode = await getReferralCodeFromKeytar(userId) // Pass userId
		console.log(
			`PROD MODE: Fetched local referral code for ${userId}:`,
			referralCode
		)
		return referralCode
	} catch (error) {
		console.error(
			`PROD MODE: Error fetching local referral code for ${userId}: ${error}`
		)
		return null
	}
})

// Fetch Local Referrer Status
ipcMain.handle("fetch-referrer-status", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) return null

	if (!app.isPackaged) return true // Dev mock

	try {
		const referrerStatus = await getReferrerStatusFromKeytar(userId) // Pass userId
		console.log(
			`PROD MODE: Fetched local referrer status for ${userId}:`,
			referrerStatus
		)
		return referrerStatus
	} catch (error) {
		console.error(
			`PROD MODE: Error fetching local referrer status for ${userId}: ${error}`
		)
		return null
	}
})

// Fetch Local Beta User Status
ipcMain.handle("fetch-beta-user-status", async () => {
	const userId = getUserIdFromProfile() // Needed for Keytar
	if (!userId && app.isPackaged) return null

	const isDev = !app.isPackaged
	if (isDev) console.log("DEV MODE: Handling fetch-beta-user-status (local).")

	try {
		const betaUserStatus = await getBetaUserStatusFromKeytar(userId) // Pass userId
		console.log(
			`${isDev ? "DEV" : "PROD"} MODE: Fetched local beta status for ${userId || "dev"}:`,
			betaUserStatus
		)
		if (isDev && betaUserStatus === null) return true // Dev default
		return betaUserStatus
	} catch (error) {
		console.error(
			`${isDev ? "DEV" : "PROD"} MODE: Error fetching local beta status: ${error}`
		)
		return null
	}
})

// --- Backend Interaction IPC Handlers (Now include Auth Header) ---

// Set Referrer (Backend Call)
ipcMain.handle("set-referrer", async (_event, { referralCode }) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	if (!app.isPackaged)
		return { message: "DEV: Referrer status simulated", status: 200 } // Dev skip

	try {
		const apiUrl = `${process.env.APP_SERVER_URL}/get-user-and-set-referrer-status`
		console.log(
			`PROD MODE: User ${userId} sending referral code ${referralCode} to ${apiUrl}`
		)
		const response = await fetch(apiUrl, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }, // Auth header
			// Backend uses token to identify user making request, body contains the code to use
			body: JSON.stringify({ referral_code: referralCode })
		})
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorText = await response.text()
			let detail = errorText
			try {
				detail = JSON.parse(errorText).detail || detail
			} catch {}
			console.error(
				`PROD MODE: Error from set-referrer API for ${userId}: ${response.status}`,
				detail
			)
			return { error: `API Error: ${detail}`, status: response.status }
		}
		const result = await response.json()
		console.log(
			`PROD MODE: Set referrer API call successful for user ${userId}:`,
			result
		)
		// Consider fetching current user's status if backend indicates it might have changed
		// await fetchAndSetReferrerStatus();
		return {
			message:
				result.message || "Referrer request processed successfully",
			status: 200
		}
	} catch (error) {
		console.error(
			`PROD MODE: Error in set-referrer IPC handler for ${userId}: ${error}`
		)
		return { error: error.message, status: 500 }
	}
})

// Invert Beta Status (Backend Call)
ipcMain.handle("invert-beta-user-status", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	if (!app.isPackaged)
		return { message: "DEV: Beta status inversion simulated", status: 200 } // Dev skip

	try {
		const apiUrl = `${process.env.APP_SERVER_URL}/get-user-and-invert-beta-user-status`
		console.log(
			`PROD MODE: Inverting beta status for user: ${userId} via ${apiUrl}`
		)
		const response = await fetch(apiUrl, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader } // Auth header
			// Backend identifies user via token, body might be empty or specific if needed
			// body: JSON.stringify({ user_id: userId }) // Body might not be needed now
		})
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorText = await response.text()
			let detail = errorText
			try {
				detail = JSON.parse(errorText).detail || detail
			} catch {}
			console.error(
				`PROD MODE: Error from invert-beta API for ${userId}: ${response.status}`,
				detail
			)
			return { error: `API Error: ${detail}`, status: response.status }
		}
		const result = await response.json()
		console.log(
			`PROD MODE: Invert beta status API call successful for user ${userId}:`,
			result
		)
		// Update local status immediately
		const currentStatus = await getBetaUserStatusFromKeytar(userId)
		const newStatus = !currentStatus
		await setBetaUserStatusInKeytar(userId, newStatus) // Use userId
		console.log(
			`PROD MODE: Updated local beta status in Keytar to: ${newStatus} for ${userId}`
		)
		return {
			message: result.message || "Beta status inverted successfully",
			status: 200
		}
	} catch (error) {
		console.error(
			`PROD MODE: Error in invert-beta-user-status IPC handler for ${userId}: ${error}`
		)
		return { error: error.message, status: 500 }
	}
})

// Set User Data (Backend Call)
ipcMain.handle("set-user-data", async (_event, args) => {
	const { data } = args
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: set-user-data called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/set-user-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ data: data }) // Backend gets userId from token
			}
		)
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorDetail = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }))
			console.error(
				`Error from set-user-data API for user ${userId}: ${response.status}`,
				errorDetail
			)
			return {
				message: `Error: ${errorDetail.detail || response.statusText}`,
				status: response.status
			}
		}
		const result = await response.json()
		console.log(`IPC: set-user-data successful for user ${userId}.`)
		return result
	} catch (error) {
		console.error(
			`IPC Error: set-user-data failed for user ${userId}: ${error}`
		)
		return {
			message: "Error storing data",
			status: 500,
			error: error.message
		}
	}
})

// Add DB Data (Backend Call)
ipcMain.handle("add-db-data", async (_event, args) => {
	const { data } = args
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: add-db-data called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/add-db-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ data: data }) // Backend gets userId from token
			}
		)
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorDetail = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }))
			console.error(
				`Error from add-db-data API for user ${userId}: ${response.status}`,
				errorDetail
			)
			return {
				message: `Error: ${errorDetail.detail || response.statusText}`,
				status: response.status
			}
		}
		const result = await response.json()
		console.log(`IPC: add-db-data successful for user ${userId}.`)
		return result
	} catch (error) {
		console.error(
			`IPC Error: add-db-data failed for user ${userId}: ${error}`
		)
		return {
			message: "Error adding data",
			status: 500,
			error: error.message
		}
	}
})

// Get User Data (Backend Call)
ipcMain.handle("get-user-data", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: get-user-data called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/get-user-data`,
			{
				method: "POST", // Keep POST, backend uses token for userId
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now if backend uses token
				// body: JSON.stringify({})
			}
		)
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorDetail = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }))
			console.error(
				`Error from get-user-data API for user ${userId}: ${response.status}`,
				errorDetail
			)
			return {
				message: `Error: ${errorDetail.detail || response.statusText}`,
				status: response.status
			}
		}
		const result = await response.json()
		console.log(`IPC: get-user-data successful for user ${userId}.`)
		return { data: result.data, status: result.status }
	} catch (error) {
		console.error(
			`IPC Error: get-user-data failed for user ${userId}: ${error}`
		)
		return {
			message: "Error fetching data",
			status: 500,
			error: error.message
		}
	}
})

// Fetch Chat History (Backend Call)
ipcMain.handle("fetch-chat-history", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: fetch-chat-history called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/get-history`,
			{
				method: "POST", // Changed to POST
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now
				// body: JSON.stringify({})
			}
		)
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorText = await response.text()
			console.error(
				`Error fetching chat history for user ${userId}: ${response.status} ${response.statusText}`,
				errorText
			)
			return {
				message: `Failed to fetch history: ${response.statusText}`,
				status: response.status,
				error: errorText
			}
		}
		const data = await response.json()
		console.log(`IPC: fetch-chat-history successful for user ${userId}.`)
		return {
			messages: data.messages,
			activeChatId: data.activeChatId,
			status: 200
		}
	} catch (error) {
		console.error(
			`IPC Error: fetch-chat-history failed for user ${userId}: ${error}`
		)
		return {
			message: "Error fetching chat history",
			status: 500,
			error: error.message
		}
	}
})

// Scrape LinkedIn (Backend Call)
ipcMain.handle("scrape-linkedin", async (_event, { linkedInProfileUrl }) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: scrape-linkedin called by user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/scrape-linkedin`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ url: linkedInProfileUrl })
			}
		)
		// ... (rest of response handling remains same) ...
		if (!response.ok) {
			const errorText = await response.text()
			console.error(
				`Error from scrape-linkedin API for user ${userId}: ${response.status}`,
				errorText
			)
			return {
				message: "Error scraping LinkedIn profile",
				status: response.status,
				error: errorText
			}
		}
		const { profile } = await response.json()
		console.log(`IPC: scrape-linkedin successful for user ${userId}.`)
		return {
			message: "LinkedIn profile scraped successfully",
			profile,
			status: 200
		}
	} catch (error) {
		console.error(
			`IPC Error: scrape-linkedin failed for user ${userId}: ${error}`
		)
		return { message: `Error: ${error.message}`, status: 500 }
	}
})

// Send Message (Backend Call) - Uses Auth Header now
ipcMain.handle("send-message", async (_event, { input }) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) {
		mainWindow?.webContents.send("chat-error", {
			message: "Cannot send message: User not authenticated."
		})
		return { message: "User not authenticated", status: 401 }
	}

	console.log(`IPC: send-message called by user ${userId}`)
	let pricing = "free" // Default
	let credits = 0 // Default

	try {
		if (app.isPackaged) {
			// Use user-specific Keytar entries
			pricing = (await getPricingFromKeytar(userId)) || "free"
			credits = await getCreditsFromKeytar(userId)
			console.log(
				`PROD MODE: User ${userId} sending message with pricing=${pricing}, credits=${credits}`
			)
		} else {
			pricing = "pro" // Dev defaults
			credits = 999
			console.log(
				`DEV MODE: User ${userId} sending message with mock pricing=${pricing}, credits=${credits}`
			)
		}

		const payload = {
			// user_id is implicit via token
			input,
			pricing,
			credits
		}
		console.log("Sending payload to /chat:", JSON.stringify(payload))

		const response = await fetch(`${process.env.APP_SERVER_URL}/chat`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }, // Auth header
			body: JSON.stringify(payload)
		})

		// --- Stream Handling (mostly same as before) ---
		if (!response.ok) {
			const errorText = await response.text()
			console.error(
				`Error from /chat endpoint for user ${userId}: ${response.status} ${response.statusText}`,
				errorText
			)
			mainWindow?.webContents.send("chat-error", {
				message: `Server error: ${response.statusText}. ${errorText}`
			})
			throw new Error(`Error sending message: Status ${response.status}`)
		}
		if (!response.body) throw new Error("Response body is null.")

		const readable = response.body
		const decoder = new TextDecoder("utf-8")
		let buffer = ""
		let finalProUsed = false
		const targetWindow = mainWindow // Assume single window for now
		if (!targetWindow) throw new Error("Application window not found.")

		console.log(
			`IPC: Starting to process chat stream for user ${userId}...`
		)
		for await (const chunk of readable) {
			buffer += decoder.decode(chunk, { stream: true })
			const splitMessages = buffer.split("\n")
			buffer = splitMessages.pop() || ""
			for (const msg of splitMessages) {
				if (msg.trim() === "") continue
				try {
					const parsed = JSON.parse(msg)
					if (
						parsed.type === "assistantStream" ||
						parsed.type === "assistantMessage"
					) {
						targetWindow.webContents.send("message-stream", {
							messageId: parsed.messageId,
							token: parsed.token || parsed.message || "",
							isFinal:
								parsed.done ||
								parsed.type === "assistantMessage"
						})
						if (parsed.proUsed) finalProUsed = true
					} else if (parsed.type === "userMessage") {
						targetWindow.webContents.send("user-message-saved", {
							id: parsed.id,
							timestamp: parsed.timestamp
						})
					} else if (parsed.type === "intermediary") {
						targetWindow.webContents.send("intermediary-message", {
							message: parsed.message,
							id: parsed.id
						})
					} else if (parsed.type === "error") {
						targetWindow.webContents.send("chat-error", {
							message: parsed.message
						})
					}
				} catch (parseError) {
					console.warn(
						`Stream parse error: ${parseError}. Msg: "${msg}"`
					)
				}
			}
		}
		// Handle remaining buffer... (same as before)
		if (buffer.trim()) {
			try {
				const parsed = JSON.parse(buffer)
				if (
					parsed.type === "assistantStream" ||
					parsed.type === "assistantMessage"
				) {
					targetWindow.webContents.send("message-stream", {
						messageId: parsed.messageId,
						token: parsed.token || parsed.message || "",
						isFinal: true
					})
					if (parsed.proUsed) finalProUsed = true
				}
			} catch (e) {
				console.error(
					`Final buffer parse error: ${e}. Buffer: "${buffer}"`
				)
			}
		}

		// Decrement credits *once*
		if (app.isPackaged && pricing === "free" && finalProUsed) {
			console.log(
				`PROD MODE: Decrementing credit for user ${userId} (Free plan, Pro feature used).`
			)
			await ipcMain.handle("decrement-pro-credits") // Uses userId internally now
		} else if (!app.isPackaged && finalProUsed) {
			console.log(
				`DEV MODE: Pro used by ${userId} (simulated), would decrement in prod if free.`
			)
		}

		console.log(`IPC: Streaming complete for user ${userId}.`)
		return { message: "Streaming complete", status: 200 }
	} catch (error) {
		console.error(
			`IPC Error: send-message handler failed for user ${userId}: ${error}`
		)
		mainWindow?.webContents.send("chat-error", {
			message: `Failed to process message: ${error.message}`
		})
		return { message: `Error: ${error.message}`, status: 500 }
	}
})

// Scrape Reddit (Backend Call)
ipcMain.handle("scrape-reddit", async (_event, { redditProfileUrl }) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: scrape-reddit called by user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/scrape-reddit`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ url: redditProfileUrl })
			}
		)
		// ... (rest of response handling) ...
		if (!response.ok) {
			/* Error handling */
		}
		const { topics } = await response.json()
		console.log(`IPC: scrape-reddit successful for user ${userId}.`)
		return {
			message: "Reddit profile scraped successfully",
			topics,
			status: 200
		}
	} catch (error) {
		/* Error handling */
	}
})

// Scrape Twitter (Backend Call)
ipcMain.handle("scrape-twitter", async (_event, { twitterProfileUrl }) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: scrape-twitter called by user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/scrape-twitter`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ url: twitterProfileUrl })
			}
		)
		// ... (rest of response handling) ...
		if (!response.ok) {
			/* Error handling */
		}
		const { topics } = await response.json()
		console.log(`IPC: scrape-twitter successful for user ${userId}.`)
		return {
			message: "Twitter profile scraped successfully",
			topics,
			status: 200
		}
	} catch (error) {
		/* Error handling */
	}
})

// Build Personality (Backend Call)
ipcMain.handle("build-personality", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: build-personality called for user ${userId}`)
	try {
		console.log(`Calling /create-document for user ${userId}...`)
		const documentResponse = await fetch(
			`${process.env.APP_SERVER_URL}/create-document`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now
				// body: JSON.stringify({})
			}
		)
		// ... (check response) ...
		if (!documentResponse.ok) {
			throw new Error("Failed create-document step")
		}
		const { personality } = await documentResponse.json()
		console.log(`Document created for ${userId}.`)

		console.log(`Updating local DB with personality for ${userId}...`)
		const addDataResponse = await fetch(
			`${process.env.APP_SERVER_URL}/add-db-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ data: { userData: { personality } } })
			}
		)
		// ... (check response) ...
		if (!addDataResponse.ok) {
			throw new Error("Failed add-db-data step")
		}
		console.log(`Local DB updated for ${userId}.`)

		console.log(`Calling /initiate-long-term-memories for ${userId}...`)
		const graphResponse = await fetch(
			`${process.env.APP_SERVER_URL}/initiate-long-term-memories`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now
				// body: JSON.stringify({})
			}
		)
		// ... (check response) ...
		if (!graphResponse.ok) {
			throw new Error("Failed initiate-long-term-memories step")
		}
		console.log(`Graph created/updated for ${userId}.`)
		return {
			message: "Document and Graph created successfully",
			status: 200
		}
	} catch (error) {
		console.error(
			`IPC Error: build-personality failed for ${userId}: ${error}`
		)
		return { message: `Error: ${error.message}`, status: 500 }
	}
})

// Reset Graph (Backend Call)
ipcMain.handle("reset-long-term-memories", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: reset-long-term-memories called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/initiate-long-term-memories`,
			{
				// Consider a dedicated /reset endpoint
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				// Send specific flag in body if needed, user identified by token
				body: JSON.stringify({ clear_graph: true })
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error("Failed reset step")
		}
		console.log(`Graph reset successfully for ${userId}.`)
		return { message: "Graph reset successfully", status: 200 }
	} catch (error) {
		console.error(
			`IPC Error: reset-long-term-memories failed for ${userId}: ${error}`
		)
		return { message: `Error: ${error.message}`, status: 500 }
	}
})

// Customize Graph (Backend Call)
ipcMain.handle(
	"customize-long-term-memories",
	async (_event, { newGraphInfo }) => {
		const userId = getUserIdFromProfile()
		const authHeader = getAuthHeader()
		if (!userId || !authHeader)
			return { error: "User not authenticated", status: 401 }

		console.log(
			`IPC: customize-long-term-memories called by user ${userId}`
		)
		let credits = 0
		let pricing = "free"

		try {
			if (app.isPackaged) {
				credits = await getCreditsFromKeytar(userId) // Use userId
				pricing = await getPricingFromKeytar(userId) // Use userId
				console.log(
					`PROD MODE: Customizing graph for ${userId}, credits=${credits}, pricing=${pricing}`
				)
			} else {
				/* Dev defaults */ credits = 999
				pricing = "pro"
				console.log(
					`DEV MODE: Customizing graph for ${userId} (mock credits)`
				)
			}

			const response = await fetch(
				`${process.env.APP_SERVER_URL}/customize-long-term-memories`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...authHeader
					},
					body: JSON.stringify({
						information: newGraphInfo,
						pricing: pricing, // Send pricing/credits for backend logic
						credits: credits
					})
				}
			)
			// ... (check response and handle credit decrement) ...
			if (!response.ok) {
				throw new Error("Failed customize step")
			}
			const result = await response.json()
			console.log(
				`Customize graph successful for user ${userId}:`,
				result
			)
			if (
				app.isPackaged &&
				pricing === "free" &&
				result?.pro_used === true
			) {
				console.log(
					`PROD MODE: Decrementing credit for ${userId} (customize graph).`
				)
				await ipcMain.handle("decrement-pro-credits") // Uses userId now
			}
			return {
				message: result.message || "Graph customized successfully",
				status: 200
			}
		} catch (error) {
			console.error(
				`IPC Error: customize-long-term-memories failed for ${userId}: ${error}`
			)
			return { message: `Error: ${error.message}`, status: 500 }
		}
	}
)

// Delete Subgraph (Backend Call)
ipcMain.handle("delete-subgraph", async (_event, { source_name }) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { status: "failure", error: "User not authenticated" }

	console.log(
		`IPC: delete-subgraph called by user ${userId} for source: ${source_name}`
	)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/delete-subgraph`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ source: source_name })
			}
		)
		// ... (check response) ...
		const result = await response.json()
		if (!response.ok || result.status === "failure") {
			throw new Error(result.error || `Server error ${response.status}`)
		}
		console.log(`Delete subgraph successful for user ${userId}:`, result)
		return result
	} catch (error) {
		console.error(
			`IPC Error: delete-subgraph failed for ${userId}: ${error}`
		)
		return { status: "failure", error: error.message }
	}
})

// Fetch Tasks (Backend Call)
ipcMain.handle("fetch-tasks", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: fetch-tasks called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/fetch-tasks`,
			{
				method: "POST", // Changed to POST
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now
				// body: JSON.stringify({})
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(`IPC: fetch-tasks successful for user ${userId}.`)
		return result
	} catch (error) {
		console.error(
			`IPC Error: fetch-tasks failed for user ${userId}:`,
			error
		)
		return { error: error.message }
	}
})

// Add Task (Backend Call)
ipcMain.handle("add-task", async (_event, taskData) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: add-task called by user ${userId} with:`, taskData)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/add-task`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ description: taskData.description }) // Backend gets user from token
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(`IPC: add-task successful for user ${userId}:`, result)
		return result
	} catch (error) {
		console.error(`IPC Error: add-task failed for user ${userId}:`, error)
		return { error: error.message }
	}
})

// Update Task (Backend Call)
ipcMain.handle(
	"update-task",
	async (_event, { taskId, description, priority }) => {
		const userId = getUserIdFromProfile()
		const authHeader = getAuthHeader()
		if (!userId || !authHeader) return { error: "User not authenticated" }

		console.log(
			`IPC: update-task called by user ${userId} for ID ${taskId}`
		)
		try {
			const response = await fetch(
				`${process.env.APP_SERVER_URL || "http://localhost:5000"}/update-task`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...authHeader
					},
					body: JSON.stringify({
						task_id: taskId,
						description,
						priority
					})
				}
			)
			// ... (check response) ...
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`)
			}
			const result = await response.json()
			console.log(
				`IPC: update-task successful for user ${userId}, task ${taskId}.`
			)
			return result
		} catch (error) {
			console.error(
				`IPC Error: update-task failed for user ${userId}, task ${taskId}:`,
				error
			)
			return { error: error.message }
		}
	}
)

// Delete Task (Backend Call)
ipcMain.handle("delete-task", async (_event, taskId) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: delete-task called by user ${userId} for ID:`, taskId)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/delete-task`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify({ task_id: taskId })
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(
			`IPC: delete-task successful for user ${userId}, task ${taskId}.`
		)
		return result
	} catch (error) {
		console.error(
			`IPC Error: delete-task failed for user ${userId}, task ${taskId}:`,
			error
		)
		return { error: error.message }
	}
})

// Fetch Short Term Memories (Backend Call)
ipcMain.handle(
	"fetch-short-term-memories",
	async (_event, { category, limit = 10 }) => {
		const userId = getUserIdFromProfile()
		const authHeader = getAuthHeader()
		if (!userId || !authHeader) return [] // Return empty array on auth error

		console.log(
			`IPC: fetch-short-term-memories called for user ${userId}, category: ${category}`
		)
		try {
			const response = await fetch(
				`${process.env.APP_SERVER_URL || "http://localhost:5000"}/get-short-term-memories`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...authHeader
					},
					body: JSON.stringify({ category, limit }) // Backend gets user from token
				}
			)
			// ... (check response) ...
			if (!response.ok) {
				throw new Error(
					`Failed to fetch memories: Status ${response.status}`
				)
			}
			const memories = await response.json()
			console.log(
				`IPC: fetch-short-term-memories successful for user ${userId}.`
			)
			return memories
		} catch (error) {
			console.error(
				`IPC Error: fetch-short-term-memories failed for user ${userId}:`,
				error
			)
			return []
		}
	}
)

// Add Short Term Memory (Backend Call)
ipcMain.handle("add-short-term-memory", async (_event, memoryData) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: add-short-term-memory called by user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/add-short-term-memory`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(memoryData) // Backend gets user from token
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(`IPC: add-short-term-memory successful for user ${userId}.`)
		return result
	} catch (error) {
		console.error(
			`IPC Error: add-short-term-memory failed for user ${userId}:`,
			error
		)
		return { error: error.message }
	}
})

// Update Short Term Memory (Backend Call)
ipcMain.handle("update-short-term-memory", async (_event, memoryData) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: update-short-term-memory called by user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/update-short-term-memory`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(memoryData) // Backend gets user from token
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(
			`IPC: update-short-term-memory successful for user ${userId}.`
		)
		return result
	} catch (error) {
		console.error(
			`IPC Error: update-short-term-memory failed for user ${userId}:`,
			error
		)
		return { error: error.message }
	}
})

// Delete Short Term Memory (Backend Call)
ipcMain.handle("delete-short-term-memory", async (_event, memoryData) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: delete-short-term-memory called by user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/delete-short-term-memory`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader },
				body: JSON.stringify(memoryData) // Backend gets user from token
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(
			`IPC: delete-short-term-memory successful for user ${userId}.`
		)
		return result
	} catch (error) {
		console.error(
			`IPC Error: delete-short-term-memory failed for user ${userId}:`,
			error
		)
		return { error: error.message }
	}
})

// Clear All Short Term Memories (Backend Call)
ipcMain.handle("clear-all-short-term-memories", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader) return { error: "User not authenticated" }

	console.log(`IPC: clear-all-short-term-memories called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/clear-all-short-term-memories`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now
				// body: JSON.stringify({})
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		const result = await response.json()
		console.log(
			`IPC: clear-all-short-term-memories successful for user ${userId}.`
		)
		return result
	} catch (error) {
		console.error(
			`IPC Error: clear-all-short-term-memories failed for user ${userId}:`,
			error
		)
		return { error: error.message }
	}
})

// Fetch Long Term Memories (Graph) (Backend Call)
ipcMain.handle("fetch-long-term-memories", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: fetch-long-term-memories called for user ${userId}`)
	try {
		const apiUrl = `${process.env.APP_SERVER_URL}/get-graph-data`
		console.log(
			`Fetching graph data for user ${userId} from backend: ${apiUrl}`
		)
		const response = await fetch(apiUrl, {
			method: "POST", // Keep POST, backend uses token for user
			headers: { "Content-Type": "application/json", ...authHeader }
			// Body likely empty now
			// body: JSON.stringify({})
		})
		// ... (check response) ...
		if (!response.ok) {
			let errorText = await response.text()
			try {
				errorText = JSON.parse(errorText).detail || errorText
			} catch {}
			console.error(
				`Error fetching graph data for ${userId}: ${response.status} ${errorText}`
			)
			return {
				error: `Failed to fetch graph data: ${errorText}`,
				status: response.status
			}
		}
		const graphData = await response.json()
		console.log(
			`IPC: fetch-long-term-memories successful for user ${userId}.`
		)
		return graphData
	} catch (error) {
		console.error(
			`IPC Error: fetch-long-term-memories failed for ${userId}: ${error}`
		)
		return {
			error: `Network or processing error: ${error.message}`,
			status: 500
		}
	}
})

// Get Notifications (Backend Call)
ipcMain.handle("get-notifications", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { error: "User not authenticated", status: 401 }

	console.log(`IPC: get-notifications called for user ${userId}`)
	try {
		const response = await fetch(
			`${process.env.APP_SERVER_URL}/get-notifications`,
			{
				method: "POST", // Changed to POST
				headers: { "Content-Type": "application/json", ...authHeader }
				// Body might be empty now
				// body: JSON.stringify({})
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			const errorDetail = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }))
			console.error(
				`Error from get-notifications API for user ${userId}: ${response.status}`,
				errorDetail
			)
			return {
				message: `Error: ${errorDetail.detail || response.statusText}`,
				status: response.status
			}
		}
		const result = await response.json()
		console.log(`IPC: get-notifications successful for user ${userId}.`)
		return { notifications: result.notifications, status: 200 }
	} catch (error) {
		console.error(
			`IPC Error: get-notifications failed for user ${userId}: ${error}`
		)
		return {
			message: "Error fetching notifications",
			status: 500,
			error: error.message
		}
	}
})

// Get Task Approval Data (Backend Call)
ipcMain.handle("get-task-approval-data", async (_event, taskId) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { status: 401, message: "User not authenticated." }
	if (!taskId) return { status: 400, message: "Task ID is required." }

	console.log(
		`IPC: get-task-approval-data called by user ${userId} for taskId: ${taskId}`
	)
	try {
		const apiUrl = `${process.env.APP_SERVER_URL || "http://localhost:5000"}/get-task-approval-data`
		const response = await fetch(apiUrl, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify({ task_id: taskId })
		})
		// ... (check response) ...
		let responseBody
		try {
			responseBody = await response.json()
		} catch {
			responseBody = { detail: await response.text() }
		}
		if (!response.ok) {
			console.error(
				`Backend error (${response.status}) for get-task-approval-data (user ${userId}):`,
				responseBody
			)
			return {
				status: response.status,
				message: responseBody.detail || `HTTP error ${response.status}`
			}
		}
		console.log(
			`IPC: get-task-approval-data successful for ${taskId} (user ${userId}).`
		)
		return { status: 200, approval_data: responseBody.approval_data }
	} catch (error) {
		console.error(
			`IPC Error: Failed to fetch approval data for ${taskId} (user ${userId}):`,
			error
		)
		return {
			status: 500,
			message: `Error fetching approval data: ${error.message}`
		}
	}
})

// Approve Task (Backend Call)
ipcMain.handle("approve-task", async (_event, taskId) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { status: 401, message: "User not authenticated." }
	if (!taskId) return { status: 400, message: "Task ID is required." }

	console.log(
		`IPC: approve-task called by user ${userId} for taskId: ${taskId}`
	)
	try {
		const apiUrl = `${process.env.APP_SERVER_URL || "http://localhost:5000"}/approve-task`
		const response = await fetch(apiUrl, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify({ task_id: taskId })
		})
		// ... (check response) ...
		let responseBody
		try {
			responseBody = await response.json()
		} catch {
			responseBody = { detail: await response.text() }
		}
		if (!response.ok) {
			console.error(
				`Backend error (${response.status}) for approve-task (user ${userId}):`,
				responseBody
			)
			return {
				status: response.status,
				message:
					responseBody.detail ||
					responseBody.message ||
					`HTTP error ${response.status}`
			}
		}
		console.log(
			`IPC: approve-task successful for ${taskId} (user ${userId}).`
		)
		return {
			status: 200,
			message: responseBody.message,
			result: responseBody.result
		}
	} catch (error) {
		console.error(
			`IPC Error: Failed to approve task ${taskId} (user ${userId}):`,
			error
		)
		return {
			status: 500,
			message: `Error approving task: ${error.message}`
		}
	}
})

// Get Data Sources (Backend Call)
ipcMain.handle("get-data-sources", async () => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	// Maybe doesn't strictly need auth? But good practice if settings are per-user.
	if (!userId || !authHeader)
		return { error: "User potentially not authenticated" }

	console.log(`IPC: get-data-sources called by user ${userId || "N/A"}`)
	try {
		// Changed to POST to potentially pass user context if needed later
		const response = await fetch(
			`${process.env.APP_SERVER_URL || "http://localhost:5000"}/get_data_sources`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
				// body: JSON.stringify({}) // Body likely empty
			}
		)
		// ... (check response) ...
		if (!response.ok) {
			throw new Error(`Failed to fetch data sources: ${response.status}`)
		}
		const data = await response.json()
		console.log(`IPC: get-data-sources successful.`)
		return data
	} catch (error) {
		console.error("Error fetching data sources:", error)
		return { error: error.message }
	}
})

// Set Data Source Enabled (Backend Call)
ipcMain.handle(
	"set-data-source-enabled",
	async (_event, { source, enabled }) => {
		const userId = getUserIdFromProfile()
		const authHeader = getAuthHeader()
		if (!userId || !authHeader) return { error: "User not authenticated" }

		console.log(`IPC: set-data-source-enabled called by user ${userId}`)
		try {
			const response = await fetch(
				`${process.env.APP_SERVER_URL || "http://localhost:5000"}/set_data_source_enabled`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...authHeader
					},
					body: JSON.stringify({ source, enabled }) // Backend gets user from token
				}
			)
			// ... (check response) ...
			if (!response.ok) {
				throw new Error(`Failed to set data source: ${response.status}`)
			}
			const data = await response.json()
			console.log(
				`IPC: set-data-source-enabled successful for user ${userId}.`
			)
			return data
		} catch (error) {
			console.error(
				`Error setting data source enabled for user ${userId}:`,
				error
			)
			return { error: error.message }
		}
	}
)

// Clear Chat History (Backend Call)
ipcMain.handle("clear-chat-history", async (_event) => {
	const userId = getUserIdFromProfile()
	const authHeader = getAuthHeader()
	if (!userId || !authHeader)
		return { status: 401, error: "User not authenticated" }

	console.log(
		`[IPC Main] Received clear-chat-history request for user ${userId}.`
	)
	const targetUrl = `${process.env.APP_SERVER_URL || "http://localhost:5000"}/clear-chat-history`
	try {
		const response = await fetch(targetUrl, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader }
			// Body might be empty now
			// body: JSON.stringify({})
		})
		// ... (check response) ...
		if (!response.ok) {
			let errorDetail = `Backend responded with status ${response.status}`
			try {
				const d = await response.json()
				errorDetail = d.detail || JSON.stringify(d)
			} catch {}
			console.error(
				`[IPC Main] Failed clear chat history for ${userId}: ${errorDetail}`
			)
			return {
				status: response.status,
				error: `Failed to clear history: ${errorDetail}`
			}
		}
		const responseData = await response.json()
		console.log(
			`[IPC Main] Backend successfully cleared chat history for user ${userId}.`
		)
		return { status: response.status, message: responseData.message }
	} catch (error) {
		console.error(
			`[IPC Main] Network error clear-chat-history for ${userId}:`,
			error
		)
		return {
			status: 500,
			error: `Failed to communicate with backend: ${error.message}`
		}
	}
})

// --- End of File ---
