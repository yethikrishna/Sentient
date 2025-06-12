import { NextResponse } from "next/server";
import { auth0 } from "@lib/auth0";
import { getBackendAuthHeader } from "@lib/auth0";

export const dynamic = "force-dynamic";

export async function POST(request) {
	const session = await auth0.getSession();
	if (!session?.user?.sub) {
		return NextResponse.json(
			{ message: "Not authenticated" },
			{ status: 401 }
		);
	}

	try {
		const formData = await request.formData();
		const audioBlob = formData.get("audio");

		if (!audioBlob) {
			return NextResponse.json(
				{ message: "No audio file provided" },
				{ status: 400 }
			);
		}

		const authHeader = await getBackendAuthHeader();
		const backendResponse = await fetch(
			`${process.env.APP_SERVER_URL}/voice/process`,
			{
				method: "POST",
				headers: { ...authHeader },
				body: formData,
				duplex: "half"
			}
		);

		if (!backendResponse.ok) {
			const errorText = await backendResponse.text();
			let errorMessage;
			try {
				const errorJson = JSON.parse(errorText);
				errorMessage =
					errorJson.detail ||
					errorJson.message ||
					"Backend voice processing failed";
			} catch (e) {
				errorMessage =
					errorText ||
					`Backend voice endpoint failed with status ${backendResponse.status}`;
			}
			throw new Error(errorMessage);
		}

		// Stream the audio response back to the client
		return new Response(backendResponse.body, {
			status: 200,
			headers: {
				"Content-Type": "audio/mpeg"
			}
		});
	} catch (error) {
		console.error("API Error in /chat/voice:", error);
		return NextResponse.json(
			{ message: "Internal Server Error", error: error.message },
			{ status: 500 }
		);
	}
}