"use server"

import { auth0 } from "@lib/auth0"
import { MongoClient } from "mongodb"
import webpush from "web-push"

// --- DB Connection ---
const MONGO_URI = process.env.MONGO_URI
const MONGO_DB_NAME = process.env.MONGO_DB_NAME

let cachedClient = null
let cachedDb = null

async function connectToDatabase() {
	if (cachedClient && cachedDb) {
		return { client: cachedClient, db: cachedDb }
	}

	if (!MONGO_URI) {
		throw new Error(
			"MONGO_URI is not defined in the environment variables."
		)
	}

	const client = new MongoClient(MONGO_URI)
	await client.connect()
	const db = client.db(MONGO_DB_NAME)

	cachedClient = client
	cachedDb = db

	return { client, db }
}

// --- WebPush Setup ---
if (
	process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY &&
	process.env.VAPID_PRIVATE_KEY &&
	process.env.VAPID_ADMIN_EMAIL
) {
	webpush.setVapidDetails(
		process.env.VAPID_ADMIN_EMAIL,
		process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
		process.env.VAPID_PRIVATE_KEY
	)
} else {
	console.warn(
		"VAPID details not fully configured. Push notifications may not work."
	)
}

// --- Server Actions ---

export async function subscribeUser(subscription) {
	const session = await auth0.getSession()
	if (!session?.user) {
		throw new Error("Not authenticated")
	}
	const userId = session.user.sub

	try {
		const { db } = await connectToDatabase()
		const userProfiles = db.collection("user_profiles")

		await userProfiles.updateOne(
			{ user_id: userId },
			{ $set: { "userData.pwa_subscription": subscription } },
			{ upsert: true }
		)

		console.log(`[Actions] Subscription saved for user: ${userId}`)
		return { success: true }
	} catch (error) {
		console.error("[Actions] Error saving subscription:", error)
		return {
			success: false,
			error: "Failed to save subscription to database."
		}
	}
}

export async function unsubscribeUser() {
	const session = await auth0.getSession()
	if (!session?.user) {
		throw new Error("Not authenticated")
	}
	const userId = session.user.sub

	try {
		const { db } = await connectToDatabase()
		const userProfiles = db.collection("user_profiles")

		await userProfiles.updateOne(
			{ user_id: userId },
			{ $unset: { "userData.pwa_subscription": "" } }
		)

		console.log(`[Actions] Subscription removed for user: ${userId}`)
		return { success: true }
	} catch (error) {
		console.error("[Actions] Error removing subscription:", error)
		return {
			success: false,
			error: "Failed to remove subscription from database."
		}
	}
}

export async function sendNotificationToCurrentUser(payload) {
	const session = await auth0.getSession()
	if (!session?.user) {
		throw new Error("Not authenticated")
	}
	const userId = session.user.sub

	if (
		!process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ||
		!process.env.VAPID_PRIVATE_KEY
	) {
		console.error(
			"[Actions] VAPID keys not configured. Cannot send push notification."
		)
		return {
			success: false,
			error: "VAPID keys not configured on the server."
		}
	}

	try {
		const { db } = await connectToDatabase()
		const userProfile = await db
			.collection("user_profiles")
			.findOne(
				{ user_id: userId },
				{ projection: { "userData.pwa_subscription": 1 } }
			)

		const subscription = userProfile?.userData?.pwa_subscription

		if (!subscription) {
			console.log(
				`[Actions] No push subscription found for user ${userId}.`
			)
			return { success: false, error: "No subscription found for user." }
		}

		await webpush.sendNotification(subscription, JSON.stringify(payload))

		console.log(
			`[Actions] Push notification sent successfully to user ${userId}.`
		)
		return { success: true }
	} catch (error) {
		console.error(
			`[Actions] Error sending push notification to user ${userId}:`,
			error
		)

		// If the subscription is expired or invalid, the push service returns an error (e.g., 410 Gone).
		// We should handle this by removing the invalid subscription from the database.
		if (error.statusCode === 410 || error.statusCode === 404) {
			console.log(
				`[Actions] Subscription for user ${userId} is invalid. Removing from DB.`
			)
			await unsubscribeUser()
		}

		return { success: false, error: "Failed to send push notification." }
	}
}
