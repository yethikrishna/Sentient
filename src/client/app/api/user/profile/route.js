// src/client/app/api/user/profile/route.js
import { NextResponse } from "next/server"
import { getSession } from "@/lib/auth"

export async function GET() {
	const session = await getSession()

	if (!session?.user) {
		return NextResponse.json(
			{ message: "Not authenticated" },
			{ status: 401 }
		)
	}

	// The user profile comes directly from the session token.
	// We ensure `given_name` is provided for the UI.
	const userProfile = {
		sub: session.user.sub,
		given_name: session.user.given_name || session.user.name || "User",
		picture:
			session.user.picture ||
			`https://i.pravatar.cc/150?u=${session.user.sub}`
	}

	return NextResponse.json(userProfile)
}