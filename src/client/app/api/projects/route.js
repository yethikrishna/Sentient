// src/client/app/api/projects/route.js
import { NextResponse } from "next/server"
import { withAuth } from "@lib/api-utils"

const appServerUrl =
	process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
		? process.env.INTERNAL_APP_SERVER_URL
		: process.env.NEXT_PUBLIC_APP_SERVER_URL

// GET: List all projects for the current user
export const GET = withAuth(async function GET(request, { authHeader }) {
	try {
		const response = await fetch(`${appServerUrl}/api/projects`, {
			method: "GET",
			headers: { "Content-Type": "application/json", ...authHeader }
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to fetch projects")
		}
		return NextResponse.json(data)
	} catch (error) {
		console.error("API Error in /api/projects (GET):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})

// POST: Create a new project
export const POST = withAuth(async function POST(request, { authHeader }) {
	try {
		const body = await request.json()
		const response = await fetch(`${appServerUrl}/api/projects`, {
			method: "POST",
			headers: { "Content-Type": "application/json", ...authHeader },
			body: JSON.stringify(body)
		})

		const data = await response.json()
		if (!response.ok) {
			throw new Error(data.detail || "Failed to create project")
		}
		return NextResponse.json(data, { status: 201 })
	} catch (error) {
		console.error("API Error in /api/projects (POST):", error)
		return NextResponse.json({ error: error.message }, { status: 500 })
	}
})
