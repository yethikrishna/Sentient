/**
 * @file Database utility functions for initializing and accessing user profile and chats databases using lowdb.
 * This module provides asynchronous functions to create and retrieve instances of lowdb databases,
 * specifically for storing user profile data and chat history. It uses JSONFilePreset for file-based storage.
 */

import { JSONFilePreset } from "lowdb/node"

/**
 * Asynchronously initializes and returns a lowdb database instance for user profiles.
 * It uses JSONFilePreset for persistent storage in a JSON file. If the database file does not exist,
 * it will be created with a default data structure.
 *
 * @async
 * @function getUserProfileDb
 * @param {string} dbPath - The file path where the user profile database JSON file will be stored.
 * @returns {Promise<lowdb.Low<object> | null>} A promise that resolves with the lowdb database instance for user profiles,
 *                                             or null if initialization fails. The database instance is typed to manage an object.
 *                                             The object is expected to have a 'userData' property.
 *                                             Example structure: { userData: { firstRunCompleted: boolean, personality: object, linkedInProfile: object } }.
 * @throws {Error} If there is an error during database initialization. Errors are logged to the console.
 *
 * @example
 * // Example usage:
 * const userProfileDb = await getUserProfileDb('/path/to/userProfileDb.json');
 * if (userProfileDb) {
 *   const firstRun = userProfileDb.data.userData.firstRunCompleted;
 *   // ... use userProfileDb instance
 * } else {
 *   console.error('Failed to initialize user profile database.');
 * }
 */
export const getUserProfileDb = async (dbPath) => {
	try {
		// Default data structure for the user profile database if it's newly created or empty.
		const defaultData = {
			userData: {
				firstRunCompleted: false, // Flag to indicate if the first run setup has been completed.
				personality: {}, // Object to store user personality data.
				linkedInProfile: {} // Object to store LinkedIn profile information.
			}
		}

		// Initialize lowdb with JSONFilePreset, providing the database file path and default data.
		const db = await JSONFilePreset(dbPath, defaultData)
		return db // Return the initialized lowdb database instance.
	} catch (error) {
		await console.log(`Error initializing user profile database: ${error}`) // Log error if initialization fails.
		return null // Return null to indicate database initialization failure.
	}
}

/**
 * Asynchronously initializes and returns a lowdb database instance for chats.
 * It uses JSONFilePreset for persistent storage in a JSON file. If the database file does not exist,
 * it will be created with a default data structure.
 *
 * @async
 * @function getChatsDb
 * @param {string} dbPath - The file path where the chats database JSON file will be stored.
 * @returns {Promise<lowdb.Low<object> | null>} A promise that resolves with the lowdb database instance for chats,
 *                                          or null if initialization fails. The database instance is typed to manage an object.
 *                                          The object is expected to have a 'chats' property which is an array of chat objects.
 *                                          Example structure: { chats: Array<Chat> }.
 * @throws {Error} If there is an error during database initialization. Errors are logged to the console.
 *
 * @example
 * // Example usage:
 * const chatsDb = await getChatsDb('/path/to/chatsDb.json');
 * if (chatsDb) {
 *   const chats = chatsDb.data.chats;
 *   // ... use chatsDb instance
 * } else {
 *   console.error('Failed to initialize chats database.');
 * }
 */
export const getChatsDb = async (dbPath) => {
	try {
		// Default data structure for the chats database if it's newly created or empty.
		const defaultData = {
			chats: [] // Array to store chat objects. Each object represents a chat session.
		}

		// Initialize lowdb with JSONFilePreset, providing the database file path and default data.
		const db = await JSONFilePreset(dbPath, defaultData)

		return db // Return the initialized lowdb database instance.
	} catch (error) {
		await console.log(`Error initializing chats database: ${error}`) // Log error if initialization fails.
		return null // Return null to indicate database initialization failure.
	}
}
