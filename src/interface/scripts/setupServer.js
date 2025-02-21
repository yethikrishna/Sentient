/**
 * @file Script to manage server setup, updates, and installation using GitHub releases and NSSM for Windows service management.
 * This script handles checking for updates from GitHub, downloading the latest server installer,
 * stopping/starting the Sentient service, and running the installer with elevated privileges using `sudo-prompt`.
 */

import { app } from "electron"
import path from "path"
import https from "https"
import fs from "fs"
import sudo from "sudo-prompt"
import { getBetaUserStatusFromKeytar } from "../utils/auth.js"

/**
 * Determines if the user is a beta user to select the correct GitHub repository for updates.
 * @constant {boolean}
 * @private
 */
const betaUserStatus = await getBetaUserStatusFromKeytar()

/**
 * GitHub API URL for fetching the latest release information, determined by beta user status.
 * @constant {string}
 */
const GITHUB_API_URL = betaUserStatus
	? "https://api.github.com/repos/existence-master/Sentient-Beta-Releases/releases/latest"
	: "https://api.github.com/repos/existence-master/Sentient-Releases/releases/latest"

/**
 * Directory where the server is installed within the user's AppData.
 * @constant {string}
 */
const SERVER_DIR = path.join(
	app.getPath("home"),
	"AppData",
	"Local",
	"Programs",
	"Sentient",
	"server"
)
/**
 * Temporary path for the server installer executable.
 * @constant {string}
 */
const TEMP_EXE = path.join(app.getPath("temp"), "ServerInstaller.exe")
/**
 * Path to the file storing the current server version.
 * @constant {string}
 */
const CURRENT_VERSION_FILE = path.join(SERVER_DIR, "version.txt")
/**
 * Path to the NSSM (Non-Sucking Service Manager) executable, used for service management on Windows.
 * @constant {string}
 */
const NSSM_PATH = path.join(SERVER_DIR, "nssm.exe")

/**
 * Checks for updates by comparing the current version with the latest version available on GitHub.
 *
 * @async
 * @returns {Promise<object|null>} Returns release information if an update is available, otherwise null.
 *         The release information object contains `version` and `downloadUrl` of the installer.
 * @throws {Error} If there is an error during the update check process.
 */
const checkForUpdates = async () => {
	try {
		const latestVersionInfo = await fetchLatestReleaseInfo() // Fetch latest release info from GitHub.
		const currentVersion = getCurrentVersion() // Get the currently installed server version.
		// Compare versions and return release info if a newer version is available.
		return latestVersionInfo.version.replace(/^v/, "") !== currentVersion
			? latestVersionInfo
			: null
	} catch (err) {
		await console.log(`Error checking updates: ${err}`) // Log any errors during update check.
		return null // Return null to indicate no update available or check failed.
	}
}

/**
 * Fetches the latest release information from GitHub API, including version and installer download URL.
 *
 * @returns {Promise<object>} A promise that resolves to an object containing the latest `version` and `downloadUrl`.
 * @throws {Error} If fetching or parsing release information fails.
 */
const fetchLatestReleaseInfo = () => {
	return new Promise((resolve, reject) => {
		// Recursive function to handle HTTP redirects.
		const handleRequest = (url) => {
			https
				.get(
					url,
					{ headers: { "User-Agent": "Electron-App" } }, // Set User-Agent to avoid being blocked.
					(res) => {
						// Handle HTTP redirects.
						if (
							res.statusCode >= 300 &&
							res.statusCode < 400 &&
							res.headers.location
						) {
							console.log(
								`Redirecting to: ${res.headers.location}`
							)
							handleRequest(res.headers.location) // Follow redirect.
						} else if (res.statusCode === 200) {
							// Successful response.
							let data = ""
							res.on("data", (chunk) => (data += chunk)) // Accumulate response data.
							res.on("end", async () => {
								// Response finished.
								try {
									const release = JSON.parse(data) // Parse JSON response.
									// Find assets for version and installer.
									const versionAsset = release.assets.find(
										(asset) => asset.name === "version.txt"
									)
									const installerAsset = release.assets.find(
										(asset) =>
											asset.name.endsWith(
												"ServerInstaller.exe"
											)
									)
									// Check if required assets are present.
									if (!versionAsset || !installerAsset) {
										reject(
											new Error(
												"Invalid release data: Missing version.txt or installer asset"
											)
										)
										return
									}
									// Fetch version content and resolve with release info.
									const version = await fetchAssetContent(
										versionAsset.browser_download_url
									)
									resolve({
										version: version.trim(),
										downloadUrl:
											installerAsset.browser_download_url
									})
								} catch (err) {
									reject(
										new Error(
											`Error parsing release data: ${err.message}`
										)
									)
								}
							})
						} else {
							// HTTP error status.
							reject(
								new Error(
									`Failed to fetch release info. HTTP status: ${res.statusCode}`
								)
							)
						}
					}
				)
				.on("error", (err) => reject(err)) // Handle network errors.
		}
		handleRequest(GITHUB_API_URL) // Start the initial request.
	})
}

/**
 * Fetches the content of a specific asset file from GitHub (e.g., version.txt).
 *
 * @param {string} assetUrl - URL of the asset to download.
 * @returns {Promise<string>} A promise that resolves with the content of the asset as a string.
 * @throws {Error} If download or handling of the asset content fails.
 */
const fetchAssetContent = (assetUrl) => {
	return new Promise((resolve, reject) => {
		// Recursive function to handle HTTP redirects.
		const handleRequest = (url) => {
			https
				.get(
					url,
					{ headers: { "User-Agent": "Electron-App" } }, // Set User-Agent header.
					(response) => {
						// Handle HTTP redirects.
						if (
							response.statusCode >= 300 &&
							response.statusCode < 400 &&
							response.headers.location
						) {
							console.log(
								`Redirecting to: ${response.headers.location}`
							)
							handleRequest(response.headers.location) // Follow redirect.
						} else if (response.statusCode === 200) {
							// Successful response.
							let content = ""
							response.on("data", (chunk) => (content += chunk)) // Accumulate content.
							response.on("end", () => resolve(content)) // Resolve with content.
						} else {
							// HTTP error status.
							reject(
								new Error(
									`Failed to fetch asset. HTTP status: ${response.statusCode}`
								)
							)
						}
					}
				)
				.on("error", reject) // Handle network errors.
		}
		handleRequest(assetUrl) // Start the initial request.
	})
}

/**
 * Gets the currently installed server version from the version.txt file.
 *
 * @async
 * @returns {Promise<string>} Current server version, defaults to "0.0.0" if file not found or error occurs.
 */
const getCurrentVersion = async () => {
	try {
		return fs.existsSync(CURRENT_VERSION_FILE)
			? fs.readFileSync(CURRENT_VERSION_FILE, "utf-8").trim() // Read version from file.
			: "0.0.0" // Default version if file doesn't exist.
	} catch (err) {
		await console.log(`Error reading current version: ${err}`) // Log error if reading fails.
		return "0.0.0" // Default version in case of error.
	}
}

/**
 * Updates the server to the latest version by downloading the installer, stopping the service,
 * running the installer, reinstalling the service, and starting the service.
 *
 * @async
 * @param {string} downloadUrl - URL to download the server installer.
 * @throws {Error} If any step in the update process fails.
 */
const updateServer = async (downloadUrl) => {
	try {
		const exePath = await downloadFile(downloadUrl, TEMP_EXE) // Download installer to temp path.
		console.log("Downloaded installer.")
		await stopSentientService() // Stop the Sentient service.
		console.log("Stopped SentientService.")
		await runInstaller(exePath) // Run the downloaded installer.
		console.log("Ran installer.")
		await reinstallSentientService() // Reinstall the Sentient service.
		console.log("Reinstalled SentientService.")
		await startSentientService() // Start the Sentient service.
		console.log("Started SentientService.")
	} catch (err) {
		await console.log(`Error updating server: ${err}`) // Log any errors during update.
		throw err // Propagate error to caller.
	}
}

/**
 * Stops the Sentient service using NSSM.
 *
 * @returns {Promise<void>} Promise that resolves when the service is successfully stopped.
 * @throws {Error} If stopping the service fails.
 */
const stopSentientService = () => {
	return new Promise((resolve, reject) => {
		sudo.exec(
			`"${NSSM_PATH}" stop SentientService`, // NSSM command to stop the service.
			{ name: "Sentient" }, // Prompt name for sudo.
			(error, stdout, stderr) => {
				if (error)
					return reject(
						new Error(
							`Failed to stop service: ${stderr || error.message}`
						)
					)
				console.log("SentientService stopped.")
				resolve() // Resolve on successful stop.
			}
		)
	})
}

/**
 * Reinstalls the Sentient service using NSSM, including removing existing service, installing new,
 * setting startup type, and description.
 *
 * @returns {Promise<void>} Promise that resolves when all reinstall commands are executed successfully.
 * @throws {Error} If any NSSM command during reinstallation fails.
 */
const reinstallSentientService = () => {
	return new Promise((resolve, reject) => {
		// Array of NSSM commands to execute for reinstallation.
		const commands = [
			`"${NSSM_PATH}" remove SentientService confirm`, // Remove existing service.
			`"${NSSM_PATH}" install SentientService "${path.join(
				SERVER_DIR,
				"app.exe"
			)}"`, // Install service for the new app.exe.
			`"${NSSM_PATH}" set SentientService Start SERVICE_AUTO_START`, // Set service to auto-start.
			`"${NSSM_PATH}" set SentientService Description "Handles background tasks for the Sentient application."` // Set service description.
		]

		// Recursive function to run commands sequentially.
		const runCommands = (index = 0) => {
			if (index >= commands.length) return resolve() // Resolve if all commands are executed.

			sudo.exec(
				commands[index], // Command to execute.
				{ name: "Sentient" }, // Prompt name for sudo.
				(error, stdout, stderr) => {
					if (error)
						return reject(
							new Error(
								`Failed command ${commands[index]}: ${
									stderr || error.message
								}`
							)
						)
					console.log(`Executed: ${commands[index]}`) // Log executed command.
					runCommands(index + 1) // Run next command.
				}
			)
		}

		runCommands() // Start executing commands.
	})
}

/**
 * Starts the Sentient service using NSSM.
 *
 * @returns {Promise<void>} Promise that resolves when the service is successfully started.
 * @throws {Error} If starting the service fails.
 */
const startSentientService = () => {
	return new Promise((resolve, reject) => {
		sudo.exec(
			`"${NSSM_PATH}" start SentientService`, // NSSM command to start the service.
			{ name: "Sentient" }, // Prompt name for sudo.
			(error, stdout, stderr) => {
				if (error)
					return reject(
						new Error(
							`Failed to start service: ${
								stderr || error.message
							}`
						)
					)
				console.log("SentientService started.")
				resolve() // Resolve on successful start.
			}
		)
	})
}

/**
 * Downloads a file from a URL to a specified destination.
 *
 * @param {string} fileUrl - URL of the file to download.
 * @param {string} destination - Local path to save the downloaded file.
 * @returns {Promise<string>} Promise that resolves with the destination path when download is complete.
 * @throws {Error} If download fails or HTTP error occurs.
 */
const downloadFile = (fileUrl, destination) => {
	return new Promise((resolve, reject) => {
		// Recursive function to handle HTTP redirects.
		const handleRequest = (url) => {
			https
				.get(url, (response) => {
					// Handle HTTP redirects.
					if (
						response.statusCode >= 300 &&
						response.statusCode < 400 &&
						response.headers.location
					) {
						console.log(
							`Redirecting to: ${response.headers.location}`
						)
						handleRequest(response.headers.location) // Follow redirect.
					} else if (response.statusCode === 200) {
						// Successful response.
						const file = fs.createWriteStream(destination) // Create write stream for destination.
						response.pipe(file) // Pipe response stream to file stream.
						file.on("finish", () => {
							// File download finished.
							file.close((err) => {
								if (err) reject(err)
								else resolve(destination) // Resolve with destination path.
							})
						})
					} else {
						// HTTP error status.
						reject(
							new Error(
								`Failed to download file. HTTP status: ${response.statusCode}`
							)
						)
					}
				})
				.on("error", (err) => {
					// Handle download errors.
					fs.unlink(destination, () => reject(err)) // Clean up destination file and reject.
				})
		}
		handleRequest(fileUrl) // Start the initial download request.
	})
}

/**
 * Runs the server installer executable with elevated privileges using `sudo-prompt`.
 *
 * @param {string} exePath - Path to the installer executable.
 * @returns {Promise<void>} Promise that resolves when the installer completes.
 * @throws {Error} If the installer fails to run.
 */
const runInstaller = (exePath) => {
	return new Promise((resolve, reject) => {
		const options = { name: "Sentient", env: { PATH: process.env.PATH } } // Options for sudo-prompt.

		sudo.exec(`"${exePath}"`, options, (error, stdout, stderr) => {
			// Execute installer with sudo privileges.
			if (error) reject(new Error(`Installer failed: ${error.message}`)) // Reject if installer fails.
			if (stderr) console.error(`Installer error: ${stderr}`) // Log installer errors.
			if (stdout) console.log(`Installer: ${stdout}`) // Log installer output.
			resolve() // Resolve when installer completes.
		})
	})
}

/**
 * Sets up the FastAPI server by checking for updates and installing or updating the server as needed.
 *
 * @async
 * @returns {Promise<object>} Returns an object indicating setup success and update status.
 *         Object contains `success: boolean` and `updateNeeded: boolean`.
 * @throws {Error} If server setup process encounters an error.
 */
const setupServer = async () => {
	try {
		console.log("Setting up FastAPI server...")

		// Ensure server directory exists.
		if (!fs.existsSync(SERVER_DIR)) {
			fs.mkdirSync(SERVER_DIR, { recursive: true })
		}

		const updateInfo = await checkForUpdates() // Check for server updates.

		console.log(`Update info: ${JSON.stringify(updateInfo)}`)

		if (updateInfo) {
			// Update server if a new version is available.
			await updateServer(updateInfo.downloadUrl)
		}

		return { success: true, updateNeeded: !!updateInfo } // Return setup success status and update needed info.
	} catch (err) {
		await console.log(`Error setting up FastAPI server: ${err}`) // Log any setup errors.
		return { success: false, error: err.message } // Return setup failure status and error message.
	}
}

export { setupServer }
