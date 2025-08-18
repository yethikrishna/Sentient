import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const formData = await request.formData()
		// The file is in the FormData object, which we forward directly.
		// The 'fetch' API will automatically set the correct 'multipart/form-data' header.

		const backendResponse = await fetch(
			`${appServerUrl}/api/files/upload`,
			{
				method: "POST",
				headers: { ...authHeader }, // Don't set Content-Type, let fetch do it
				body: formData,
				duplex: "half"
			}
		)

		const data = await backendResponse.json()

		if (!backendResponse.ok) {
			return NextResponse.json(
				{ error: data.detail || "Failed to upload file" },
				{ status: backendResponse.status }
			)
		}

		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /files/upload:", error)
		return NextResponse.json(
			{ error: "Internal Server Error", details: error.message },
			{ status: 500 }
		)
	}
})
