"use client"

import React, {
	useState,
	useEffect,
	useRef,
	useCallback,
	forwardRef,
	useImperativeHandle
} from "react"
import { BackgroundCircles } from "./background-circles"
import { WebRTCClient } from "@lib/webrtc-client"

const BackgroundCircleProvider = forwardRef(
	({ onStatusChange, onEvent, connectionStatusProp }, ref) => {
		const [audioLevel, setAudioLevel] = useState(0)
		const audioRef = useRef(null)
		const webrtcClientRef = useRef(null)

		const handleConnected = useCallback(() => {
			onStatusChange?.("connected")
		}, [onStatusChange])

		const handleDisconnected = useCallback(() => {
			onStatusChange?.("disconnected")
		}, [onStatusChange])

		const handleAudioStream = useCallback((stream) => {
			if (audioRef.current) {
				audioRef.current.srcObject = stream
			}
		}, [])

		const handleAudioLevel = useCallback((level) => {
			setAudioLevel((prev) => prev * 0.7 + level * 0.3)
		}, [])

		useImperativeHandle(ref, () => ({
			async connect(deviceId, authToken, rtcToken) {
				if (webrtcClientRef.current) {
					webrtcClientRef.current.disconnect()
				}
				const client = new WebRTCClient({
					onConnected: handleConnected,
					onDisconnected: handleDisconnected,
					onAudioStream: handleAudioStream,
					onAudioLevel: handleAudioLevel,
					onEvent: onEvent
				})
				webrtcClientRef.current = client
				await client.connect(deviceId, authToken, rtcToken)
			},
			disconnect() {
				webrtcClientRef.current?.disconnect()
			}
		}))

		useEffect(() => {
			// Cleanup on unmount
			return () => {
				webrtcClientRef.current?.disconnect()
			}
		}, [])

		return (
			<div className="relative w-full h-full">
				<BackgroundCircles
					audioLevel={audioLevel}
					isActive={connectionStatusProp === "connected"}
				/>
				<audio ref={audioRef} autoPlay playsInline hidden />
			</div>
		)
	}
)

BackgroundCircleProvider.displayName = "BackgroundCircleProvider"
export default BackgroundCircleProvider
