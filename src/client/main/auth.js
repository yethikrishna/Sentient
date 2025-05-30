import { app, BrowserWindow } from "electron" // Importing app and BrowserWindow class from electron module
import serve from "electron-serve" // Importing electron-serve for serving static files
import path, { dirname } from "path" // Importing path module for path manipulation
import { fileURLToPath } from "url"
import {
	getAuthenticationURL, // Importing function to get authentication URL
	loadTokens, // Importing function to load tokens after authentication
	getLogOutUrl, // Importing function to get logout URL
	logout // Importing function to perform logout
} from "../utils/auth.js"
import { checkValidity } from "./index.js" // Importing function to check token validity

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const appServe = serve({
	directory: path.join(__dirname, "../"),
	is_dev: process.env.ELECTRON_APP_URL ? true : false
})
const appOutDir = path.join(__dirname, "../")

/**
 * Creates and displays a BrowserWindow for user authentication.
 *
 * This function is responsible for setting up and displaying an Electron BrowserWindow
 * that loads the authentication URL. It also handles the OAuth2 callback, token loading,
 * and window lifecycle management for the authentication process.
 *
 * @async
 * @function createAuthWindow
 * @returns {void}
 */
export function createAuthWindow(mainWindow) {
	mainWindow.loadURL(getAuthenticationURL()) // Load authentication URL in the window

	const {
		session: { webRequest }
	} = mainWindow.webContents // Destructure webRequest from webContents session

	const filter = {
		urls: ["http://localhost/callback*"] // Filter for web requests to callback URL
	}

	// Listener for onBeforeRequest event for URLs matching the filter
	webRequest.onBeforeRequest(filter, async ({ url }) => {
		await loadTokens(url) // Load tokens from the callback URL
		await checkValidity() // Check validity of the loaded tokens

		if (process.env.ELECTRON_APP_URL) {
			mainWindow.loadURL(process.env.ELECTRON_APP_URL)
		} else {
			appServe(mainWindow).then(() => {
				mainWindow.loadURL("app://-")
			})
		}
	})
}
