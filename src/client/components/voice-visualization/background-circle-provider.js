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
			// Accept chatId
			if (voiceClient) {
				console.log(
					"[Provider] Disconnecting existing voice client first."
				)
				await voiceClient.disconnect()
			}
			console.log("[Provider] Creating new WebRTCClient")
			const client = new WebRTCClient({
				onConnected: handleConnected,
				onDisconnected: handleDisconnected,
				onConnectError: handleConnectError,
				onMessage: handleMessage,
				onAudioLevel: handleAudioLevelUpdate,
				onAudioStream: onAudioStream // Pass the remote stream handler
			})
			setVoiceClient(client)

			if (internalStatus === "disconnected") {
				console.log("[Provider] connect() called via ref")
				setInternalStatus("connecting")
				onStatusChange?.("connecting")
				try {
					// Pass token and chatId to the WebRTC client's connect method
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
			if (voiceClient && internalStatus !== "disconnected") {
				console.log("[Provider] disconnect() called via ref")
				voiceClient.disconnect()
			}
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
