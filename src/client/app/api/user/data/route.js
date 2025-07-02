// src/client/app/api/user/data/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(
			`${process.env.NEXT_PUBLIC_APP_SERVER_URL}/api/get-user-data`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}
		)

		const data = await response.json()
		if (!response.ok) {
			throw new Error(
				data.message || "Failed to fetch user data from backend"
			)
		}

		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /user/data:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
})
