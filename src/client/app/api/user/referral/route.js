// src/client/app/api/user/referral/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		// Fetch both details in parallel
		const [codeRes, statusRes] = await Promise.all([
			fetch(`${process.env.APP_SERVER_URL}/api/utils/get-referral-code`, {
				method: "POST",
				headers: { "Content-Type": "application/json", ...authHeader }
			}),
			fetch(
				`${process.env.APP_SERVER_URL}/api/utils/get-referrer-status`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...authHeader
					}
				}
			)
		])

		const codeData = await codeRes.json()
		const statusData = await statusRes.json()

		if (!codeRes.ok || !statusRes.ok) {
			throw new Error(
				codeData.message ||
					statusData.message ||
					"Failed to fetch referral details"
			)
		}

		return NextResponse.json({
			referralCode: codeData.referralCode,
			referrerStatus: statusData.referrerStatus
		})
	} catch (error) {
		console.error("API Error in /user/referral:", error)
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		)
	}
})
