// src/client/main/auth.js
import { app, BrowserWindow } from "electron" // Importing app and BrowserWindow class from electron module
import serve from "electron-serve" // Importing electron-serve for serving static files
import path, { dirname } from "path" // Importing path module for path manipulation
import { fileURLToPath } from "url"
import fetch from "node-fetch"; // Added fetch for server communication
import {
	getAuthenticationURL, // Importing function to get authentication URL
	loadTokens, // Importing function to load tokens after authentication
	getAccessToken, // To get access token for server call
	logout // Importing function to perform logout
} from "../utils/auth.js"
import { checkValidity } from "./index.js" // Importing function to check token validity

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const appServe = serve({
	directory: path.join(__dirname, "../"),
	is_dev: process.env.ELECTRON_APP_URL ? true : false
})
// const appOutDir = path.join(__dirname, "../") // Not used here

/**
 * Creates and displays a BrowserWindow for user authentication.
 *
 * This function is responsible for setting up and displaying an Electron BrowserWindow
 * that loads the authentication URL. It also handles the OAuth2 callback, token loading,
 * and window lifecycle management for the authentication process.
 * After tokens are loaded client-side (and refresh token stored in Keytar),
 * it sends the new refresh token to the main server for storage in MongoDB.
 *
 * @async
 * @function createAuthWindow
 * @returns {void}
 */
export function createAuthWindow() {
	const authWindow = new BrowserWindow({
		width: 800,
		height: 600,
		show: false, // Don't show until ready
		webPreferences: {
			nodeIntegration: false,
			contextIsolation: true,
			preload: path.join(__dirname, "preload.js")
		}
	})

	authWindow.loadURL(getAuthenticationURL()) // Load authentication URL in the window

	authWindow.once("ready-to-show", () => {
		authWindow.show()
	})

	const {
		session: { webRequest }
	} = authWindow.webContents // Destructure webRequest from webContents session

	const filter = {
		urls: ["http://localhost/callback*"] // Filter for web requests to callback URL
	}

	// Listener for onBeforeRequest event for URLs matching the filter
	webRequest.onBeforeRequest(filter, async ({ url }) => {
		try {
			console.log("[AuthWindow] Callback URL intercepted:", url);
			const tokenData = await loadTokens(url); // loadTokens now returns the raw refresh token
			console.log("[AuthWindow] Tokens loaded client-side (Keytar updated).");

			if (tokenData && tokenData.rawRefreshToken) {
				console.log("[AuthWindow] Attempting to store Auth0 refresh token on server...");
				const serverStoreUrl = `${process.env.APP_SERVER_URL}/auth/store_session`;
				const serverStorePayload = { refresh_token: tokenData.rawRefreshToken };
				
				const currentAccessToken = getAccessToken(); // Get the newly acquired access token
				if (!currentAccessToken) {
					console.error("[AuthWindow] Critical: Access token not available after loadTokens for server call.");
					// Decide how to handle - maybe proceed to checkValidity which might trigger re-auth
				} else {
					try {
						const serverResponse = await fetch(serverStoreUrl, {
							method: "POST",
							headers: {
								"Content-Type": "application/json",
								"Authorization": `Bearer ${currentAccessToken}`
							},
							body: JSON.stringify(serverStorePayload)
						});
						if (!serverResponse.ok) {
							const errorText = await serverResponse.text();
							console.error(`[AuthWindow] Failed to store refresh token on server: ${serverResponse.status} - ${errorText}`);
						} else {
							const serverResult = await serverResponse.json();
							console.log("[AuthWindow] Successfully sent Auth0 refresh token to server:", serverResult.message);
						}
					} catch (e) {
						console.error("[AuthWindow] Error sending Auth0 refresh token to server:", e);
					}
				}
			} else {
				console.warn("[AuthWindow] Did not receive refresh token from loadTokens, cannot store on server.");
			}

			// Proceed to check validity (which loads main app or onboarding)
			await checkValidity(); 
			// checkValidity handles loading the correct URL into mainWindow
			// The authWindow can be closed after this as its job is done.
			// No, checkValidity *might* create a new authWindow if checks fail.
			// Only close if checkValidity succeeds implicitly by not throwing.
			
			// If checkValidity completes without throwing an error, it means the main window
			// should be loading the correct content. Close the auth window.
			// If checkValidity throws, it will likely call createAuthWindow again, so this one should close.
			// authWindow.close() is problematic here if checkValidity fails and tries to open another authWindow
			// Best practice: checkValidity should signal success or mainWindow.loadURL itself.
			// The original code has authWindow.loadURL and then authWindow.close() *after* checkValidity.
			// This means checkValidity must ensure mainWindow is appropriately handled.
			// For simplicity, let's assume checkValidity will handle mainWindow and we just close authWindow.
			// If checkValidity throws, this close might happen before a new auth window is created.
			
		} catch (error) {
			console.error("[AuthWindow] Error during token processing or validity check:", error);
			// If an error occurs (e.g., loadTokens fails, or checkValidity decides re-auth is needed),
			// `checkValidity` might call `createAuthWindow` again.
			// To prevent issues, ensure this window is closed *before* a new one might be created.
			if (!authWindow.isDestroyed()) {
				authWindow.close();
			}
			// `checkValidity` will handle re-opening `createAuthWindow` if necessary.
			return; // Stop further processing in this callback.
		}
		
		// If everything up to here was successful, checkValidity would have loaded the correct page in mainWindow.
		// So, this authWindow can be closed.
		if (!authWindow.isDestroyed()) {
			authWindow.close();
		}
	})
}
