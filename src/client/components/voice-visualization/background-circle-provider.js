"use client"

import {
	useState,
	useEffect,
	useRef,
	useCallback,
	useImperativeHandle,
	forwardRef
} from "react"
import { VoiceBlobs } from "@components/voice-visualization/VoiceBlobs"
import { WebRTCClient } from "@utils/webRTCClient" // Use WebRTCClient instead
import React from "react"

const BackgroundCircleProviderComponent = (
	{ onStatusChange, onEvent, connectionStatusProp, onAudioStream },
	ref
) => {
	const [voiceClient, setVoiceClient] = useState(null)
	const [internalStatus, setInternalStatus] = useState("disconnected")
	const eventSourceRef = useRef(null) // Ref for EventSource
	const [audioLevel, setAudioLevel] = useState(0)

	useEffect(() => {
		if (connectionStatusProp !== internalStatus) {
			setInternalStatus(connectionStatusProp)
			if (connectionStatusProp === "disconnected") {
				setAudioLevel(0)
			}
		}
	}, [connectionStatusProp, internalStatus])

	const handleConnected = useCallback(() => {
		setInternalStatus("connected")
		onStatusChange?.("connected")
	}, [onStatusChange])

	const handleDisconnected = useCallback(() => {
		setInternalStatus("disconnected")
		setAudioLevel(0)
		onStatusChange?.("disconnected")
	}, [onStatusChange])

	const handleConnectError = useCallback(
		(error) => {
			console.error("Provider: Connection Error", error)
			setInternalStatus("disconnected")
			setAudioLevel(0)
			onStatusChange?.("disconnected")
			onEvent?.({
				type: "error",
				message: error.message || "Connection failed"
			}) // Pass error to UI
		},
		[onStatusChange, onEvent]
	)

	// handleMessage is no longer needed as SSE will handle messages
	// const handleMessage = useCallback(
	// 	(message) => {
	// 		onEvent?.(message)
	// 	},
	// 	[onEvent]
	// )

	const handleAudioLevelUpdate = useCallback((level) => {
		setAudioLevel((prev) => prev * 0.7 + level * 0.3)
	}, [])

	useImperativeHandle(ref, () => ({
		connect: async (deviceId, token, chatId) => {
			if (voiceClient) {
				console.log(
					"[Provider] Disconnecting existing voice client first."
				)
				voiceClient.disconnect()
			}
			// Close any existing EventSource before creating a new WebRTC client
			if (eventSourceRef.current) {
				eventSourceRef.current.close()
				eventSourceRef.current = null
				console.log(
					"[Provider] Existing EventSource connection closed."
				)
			}

			console.log("[Provider] Creating new WebRTCClient")
			// We define onConnected here to set up the EventSource after WebRTC connects.
			const client = new WebRTCClient({
				onConnected: () => {
					handleConnected() // Call the original handler
					// After successful WebRTC connection, open EventSource for updates
					const webrtcId = client.webrtcId // Assuming WebRTCClient exposes this ID
					if (!webrtcId) {
						console.error(
							"WebRTC ID not available after connection."
						)
						handleConnectError(new Error("Missing WebRTC ID."))
						return
					}
					const eventSourceUrl = `/api/voice/updates?webrtc_id=${webrtcId}`
					console.log(
						`[Provider] Connecting to SSE endpoint: ${eventSourceUrl}`
					)
					eventSourceRef.current = new EventSource(eventSourceUrl)

					eventSourceRef.current.onmessage = (event) => {
						try {
							const data = JSON.parse(event.data)
							onEvent?.(data)
						} catch (e) {
							console.error(
								"[Provider] Error parsing SSE message:",
								e
							)
						}
					}
					eventSourceRef.current.onerror = (err) => {
						console.error("[Provider] EventSource error:", err)
						// Only call handleConnectError if it's a real error, not just a close
						if (
							eventSourceRef.current?.readyState ===
							EventSource.CLOSED
						) {
							console.log(
								"[Provider] EventSource closed normally."
							)
						} else {
							handleConnectError(
								new Error("EventSource connection failed.")
							)
						}
						eventSourceRef.current?.close()
					}
				},
				onDisconnected: handleDisconnected,
				onConnectError: handleConnectError,
				// onMessage is no longer needed as we use SSE
				onAudioLevel: handleAudioLevelUpdate,
				onAudioStream: onAudioStream // Pass the remote stream handler
			})
			setVoiceClient(client)

			if (internalStatus === "disconnected") {
				console.log("[Provider] connect() called via ref")
				setInternalStatus("connecting")
				onStatusChange?.("connecting")
				try {
					await client.connect(deviceId, token, chatId)
				} catch (error) {
					console.error(
						"[Provider] Error during connect() call:",
						error
					)
					throw error
				}
			}
		},
		disconnect: () => {
			console.log("[Provider] disconnect() called via ref")
			if (voiceClient) {
				voiceClient.disconnect()
			}
			if (eventSourceRef.current) {
				eventSourceRef.current.close()
				eventSourceRef.current = null
				console.log("[Provider] EventSource connection closed.")
			}
			handleDisconnected() // Explicitly set status to disconnected
		}
	}))

	// Cleanup on unmount
	useEffect(() => {
		return () => {
			voiceClient?.disconnect()
			if (eventSourceRef.current) eventSourceRef.current.close()
		}
	}, [voiceClient])

	return (
		<div className="relative w-full h-full flex items-center justify-center">
			<VoiceBlobs
				audioLevel={audioLevel}
				isActive={internalStatus === "connected"}
				isConnecting={internalStatus === "connecting"}
			/>
		</div>
	)
}

const ForwardedBackgroundCircleProvider = forwardRef(
	BackgroundCircleProviderComponent
)
ForwardedBackgroundCircleProvider.displayName = "BackgroundCircleProvider"

export default ForwardedBackgroundCircleProvider
export { BackgroundCircleProviderComponent as BackgroundCircleProvider }
