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

	const handleMessage = useCallback(
		(message) => {
			onEvent?.(message)
		},
		[onEvent]
	)

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

			// Set status to connecting here, as this method is the entry point for connection.
			console.log(
				"[Provider] connect() called. Setting status to connecting."
			) // Debug log for connection attempt
			setInternalStatus("connecting")
			onStatusChange?.("connecting")

			// Initialize WebRTCClient if not already done or if it was cleaned up
			const newClient = new WebRTCClient({
				onConnected: handleConnected,
				onDisconnected: handleDisconnected,
				onConnectError: handleConnectError,
				onMessage: handleMessage,
				onAudioLevel: handleAudioLevelUpdate,
				onAudioStream: onAudioStream
			})
			setVoiceClient(newClient) // Store the client instance

			// The parent component (Chat.js) already ensures this 'connect' is called
			// only when appropriate (i.e., when currently disconnected).
			// So, we proceed to connect the WebRTCClient directly.
			try {
				console.log("[Provider] Attempting to connect WebRTCClient...")
				await newClient.connect(deviceId, token, chatId)
			} catch (error) {
				// Catch any error during the connection attempt
				console.error(
					"[Provider] Error during client.connect() call:",
					error
				)
				handleConnectError(error) // Use the provider's error handler
				throw error // Re-throw to allow Chat.js to also catch it if needed.
			}
		},
		disconnect: () => {
			console.log("[Provider] disconnect() called via ref")
			if (voiceClient) {
				voiceClient.disconnect()
			}
			handleDisconnected() // Explicitly set status to disconnected
		}
	}))

	// Cleanup on unmount
	useEffect(() => {
		return () => {
			voiceClient?.disconnect()
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
