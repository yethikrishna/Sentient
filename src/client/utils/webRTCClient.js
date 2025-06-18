// src/client/utils/webRTCClient.js
export class WebRTCClient {
	peerConnection = null
	mediaStream = null
	dataChannel = null
	options
	webrtcId = null
	audioContext = null
	analyser = null
	dataArray = null
	animationFrameId = null

	signalingServerUrl =
		process.env.NEXT_PUBLIC_APP_SERVER_URL || "http://localhost:5000"

	constructor(options = {}) {
		this.options = options
		console.log(
			`[WebRTCClient] Initialized. Signaling URL: ${this.signalingServerUrl}`
		)
	}

	async connect(deviceId, token, chatId) {
		try {
			console.log(
				"%c[WebRTCClient] 1. connect() called.",
				"color: #00A36C"
			)
			if (
				this.peerConnection &&
				(this.peerConnection.connectionState === "connected" ||
					this.peerConnection.connectionState === "connecting")
			) {
				console.warn(
					"[WebRTCClient] Already connected or connecting. Disconnecting existing connection."
				)
				this.disconnect() // Ensure a clean state before attempting a new connection
			}

			// Step 1: Generate a webrtcId for this session
			console.log(
				"%c[WebRTCClient] 2. Generating webrtcId...",
				"color: #00A36C"
			)
			this.webrtcId = `client_${Math.random().toString(36).substring(7)}`
			console.log(
				`[WebRTCClient] Attempting to connect with webrtcId: ${this.webrtcId}, deviceId: ${deviceId || "default"}`
			)
			console.log(`[WebRTCClient] Chat Context: chatId=${chatId}`)

			console.log(
				"%c[WebRTCClient] 3. Creating RTCPeerConnection...",
				"color: #00A36C"
			)
			this.peerConnection = new RTCPeerConnection({
				iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
			})

			// PeerConnection Event Handlers
			this.peerConnection.ontrack = (event) => {
				console.log(
					"[WebRTCClient] Remote track received:",
					event.track,
					event.streams
				)
				if (
					this.options.onAudioStream &&
					event.streams &&
					event.streams[0]
				) {
					this.options.onAudioStream(event.streams[0])
				}
			}

			this.peerConnection.onicecandidate = async (event) => {
				if (event.candidate) {
					// console.log("[WebRTCClient] New ICE candidate:", event.candidate); // Too verbose for production
					await fetch(`${this.signalingServerUrl}/webrtc/offer`, {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							Authorization: `Bearer ${token}`
						},
						body: JSON.stringify({
							candidate: event.candidate.toJSON(),
							webrtc_id: this.webrtcId,
							type: "ice-candidate"
						})
					})
				}
			}

			this.peerConnection.oniceconnectionstatechange = () => {
				console.log(
					"%c[WebRTCClient] ICE connection state change:",
					"color: yellow",
					this.peerConnection.iceConnectionState
				)
				if (
					this.peerConnection.iceConnectionState === "failed" ||
					this.peerConnection.iceConnectionState === "disconnected" ||
					this.peerConnection.iceConnectionState === "closed"
				) {
					console.error(
						`[WebRTCClient] ICE connection failed or disconnected: ${this.peerConnection.iceConnectionState}`
					)
					if (this.options.onConnectError) {
						this.options.onConnectError(
							new Error(
								`ICE connection state: ${this.peerConnection.iceConnectionState}`
							)
						)
					}
					this.disconnect() // Ensure cleanup on critical ICE state
				}
			}

			this.peerConnection.onconnectionstatechange = () => {
				console.log(
					"%c[WebRTCClient] PeerConnection state change:",
					"color: yellow",
					this.peerConnection.connectionState
				)
				if (this.peerConnection.connectionState === "connected") {
					if (this.options.onConnected) {
						this.options.onConnected()
					}
				} else if (
					["disconnected", "failed", "closed"].includes(
						this.peerConnection.connectionState
					)
				) {
					console.warn(
						`[WebRTCClient] PeerConnection state is ${this.peerConnection.connectionState}. Disconnecting.`
					)
					this.disconnect()
				}
			}

			// Data Channel setup (for text messages)
			this.dataChannel =
				this.peerConnection.createDataChannel("textDataChannel")
			this.dataChannel.onopen = () =>
				console.log("[WebRTCClient] Data channel opened.")
			this.dataChannel.onclose = () =>
				console.log("[WebRTCClient] Data channel closed.")
			this.dataChannel.onmessage = (event) => {
				console.log(
					"[WebRTCClient] Data channel message received:",
					event.data
				)
				if (this.options.onMessage) {
					try {
						this.options.onMessage(JSON.parse(event.data))
					} catch (e) {
						console.error(
							"[WebRTCClient] Error parsing data channel message:",
							e
						)
					}
				}
			}

			this.peerConnection.ondatachannel = (event) => {
				const receiveChannel = event.channel
				console.log(
					"[WebRTCClient] Remote data channel received:",
					receiveChannel.label
				)
				receiveChannel.onmessage = this.dataChannel.onmessage // Reuse local message handler
				receiveChannel.onopen = () =>
					console.log(
						`[WebRTCClient] Remote data channel '${receiveChannel.label}' opened.`
					)
				receiveChannel.onclose = () =>
					console.log(
						`[WebRTCClient] Remote data channel '${receiveChannel.label}' closed.`
					)
			}

			// Get user media (microphone)
			console.log(
				"%c[WebRTCClient] 4. Requesting user media (microphone)...",
				"color: #00A36C"
			)
			try {
				const constraints = {
					audio: {
						...(deviceId ? { deviceId: { exact: deviceId } } : {}),
						sampleRate: 16000,
						echoCancellation: true,
						noiseSuppression: true
					},
					video: false
				}
				this.mediaStream =
					await navigator.mediaDevices.getUserMedia(constraints)
				console.log(
					"%c[WebRTCClient] 4a. SUCCESS: Got user media.",
					"color: green",
					constraints
				)
			} catch (mediaError) {
				console.error("[WebRTCClient] Media access error:", mediaError)
				if (this.options.onConnectError) {
					this.options.onConnectError(mediaError)
				}
				if (mediaError.name === "NotAllowedError") {
					throw new Error(
						"Microphone access denied. Please allow microphone access and try again."
					)
				} else if (
					mediaError.name === "NotFoundError" ||
					mediaError.name === "DevicesNotFoundError"
				) {
					throw new Error(
						"Selected microphone not found or no microphone detected. Please check your microphone settings and try again."
					)
				} else if (mediaError.name === "OverconstrainedError") {
					throw new Error(
						`Could not satisfy microphone constraints (e.g. sample rate). Device: ${deviceId}. Error: ${mediaError.message}`
					)
				}
				throw mediaError // Re-throw to propagate the error
			}

			console.log(
				"%c[WebRTCClient] 5. Adding local tracks to peer connection...",
				"color: #00A36C"
			)
			// Add local audio track to PeerConnection
			this.mediaStream.getTracks().forEach((track) => {
				if (this.peerConnection) {
					// Defensive check
					this.peerConnection.addTrack(track, this.mediaStream)
				}
			})
			console.log("[WebRTCClient] Local tracks added to PeerConnection.")

			// Setup audio analysis for local mic level visualization
			if (this.options.onAudioLevel && this.mediaStream) {
				console.log(
					"%c[WebRTCClient] 6. Setting up audio analysis...",
					"color: #00A36C"
				)
				this.setupAudioAnalysis(this.mediaStream)
			}

			console.log(
				"%c[WebRTCClient] 7. Creating SDP offer...",
				"color: #00A36C"
			)
			// Create and send SDP offer
			const offer = await this.peerConnection.createOffer()
			await this.peerConnection.setLocalDescription(offer)
			console.log(
				"%c[WebRTCClient] 7a. SUCCESS: Offer created and local description set.",
				"color: green"
			)

			const urlWithParams = `${this.signalingServerUrl}/webrtc/offer?token=${encodeURIComponent(token)}&chat_id=${chatId || ""}`
			console.log(
				`%c[WebRTCClient] 8. Sending POST offer to signaling server: ${urlWithParams}`,
				"color: #00A36C"
			)

			const offerPayload = {
				sdp: offer.sdp, // Use sdp property directly
				type: offer.type, // Use type property directly
				webrtc_id: this.webrtcId
			}

			console.log("[WebRTCClient] Offer Payload:", offerPayload)

			// Send the offer, token, and chat_id to the fastrtc endpoint
			let response
			try {
				response = await fetch(urlWithParams, {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Accept: "application/json"
					},
					mode: "cors", // Crucial for cross-origin requests
					body: JSON.stringify(offerPayload)
				})
				console.log(
					"%c[WebRTCClient] 8a. SUCCESS: Fetch POST request sent.",
					"color: green"
				)
			} catch (networkError) {
				console.error(
					"%c[WebRTCClient] 8b. FATAL: Network error sending offer. Is the server running? Is the URL correct?",
					"color: red; font-weight: bold",
					networkError
				)
				this.options.onConnectError?.(networkError)
				this.disconnect()
				return
			}

			if (!response.ok) {
				const errorText = await response.text()
				console.error(
					`%c[WebRTCClient] 8c. FATAL: Signaling server returned an error: ${response.status} - ${errorText}`,
					"color: red; font-weight: bold"
				)
				throw new Error(
					`Signaling server request failed: ${response.status} - ${errorText}`
				)
			}

			const serverResponse = await response.json()
			console.log(
				"%c[WebRTCClient] 9. Received answer SDP from server.",
				"color: #00A36C",
				serverResponse
			)
			await this.peerConnection.setRemoteDescription(
				new RTCSessionDescription(serverResponse)
			)
			console.log(
				"%c[WebRTCClient] 10. SUCCESS: Remote description set. Connection should be established.",
				"color: green; font-weight: bold"
			)
		} catch (error) {
			// This will catch any error during the connection process, including getUserMedia or fetch failures
			console.error("[WebRTCClient] CRITICAL ERROR in connect():", error)
			this.disconnect()
			if (this.options.onConnectError) {
				this.options.onConnectError(error)
			}
			throw error // Re-throw to allow caller to handle UI updates
		}
	}

	setupAudioAnalysis(streamToAnalyze) {
		if (!streamToAnalyze) {
			console.warn(
				"[WebRTCClient] No stream provided for audio analysis."
			)
			return
		}

		try {
			this.audioContext = new (window.AudioContext ||
				window.webkitAudioContext)({ sampleRate: 16000 })
			this.analyser = this.audioContext.createAnalyser()
			this.analyser.fftSize = 256 // Smaller FFT size for faster processing, good for voice
			this.analyser.smoothingTimeConstant = 0.3 // Smooths out the visualization

			const source =
				this.audioContext.createMediaStreamSource(streamToAnalyze)
			source.connect(this.analyser)

			const bufferLength = this.analyser.frequencyBinCount
			this.dataArray = new Uint8Array(bufferLength)

			this.startAnalysisLoop()
			console.log(
				"[WebRTCClient] Audio analysis setup complete for local mic."
			)
		} catch (error) {
			console.error(
				"[WebRTCClient] Error setting up audio analysis:",
				error
			)
		}
	}

	startAnalysisLoop() {
		if (!this.analyser || !this.dataArray || !this.options.onAudioLevel)
			return

		let lastUpdateTime = 0
		const throttleInterval = 100 // Update audio level every 100ms

		const analyze = () => {
			if (!this.analyser || !this.dataArray) {
				this.animationFrameId = null
				return
			}
			this.analyser.getByteFrequencyData(this.dataArray)

			const currentTime = performance.now()
			if (currentTime - lastUpdateTime > throttleInterval) {
				let sum = 0
				for (let i = 0; i < this.dataArray.length; i++) {
					sum += this.dataArray[i]
				}
				const average = sum / this.dataArray.length
				const normalizedLevel = average / 128.0 // Normalize to 0-1 range (max value for Uint8Array is 255, so 128 is roughly half)

				const amplifiedLevel = Math.min(normalizedLevel * 1.5, 1.0) // Amplify for better visual feedback, cap at 1.0

				this.options.onAudioLevel(amplifiedLevel)
				lastUpdateTime = currentTime
			}
			this.animationFrameId = requestAnimationFrame(analyze)
		}
		this.animationFrameId = requestAnimationFrame(analyze)
	}

	stopAnalysis() {
		if (this.animationFrameId !== null) {
			cancelAnimationFrame(this.animationFrameId)
			this.animationFrameId = null
		}
		if (this.audioContext && this.audioContext.state !== "closed") {
			this.audioContext
				.close()
				.catch((e) =>
					console.error(
						"[WebRTCClient] Error closing AudioContext:",
						e
					)
				)
			this.audioContext = null
		}
		this.analyser = null
		this.dataArray = null
		console.log(
			"[WebRTCClient] Audio analysis stopped and resources released."
		)
	}

	disconnect() {
		console.log("[WebRTCClient] Disconnecting...")
		this.stopAnalysis()

		if (this.mediaStream) {
			this.mediaStream.getTracks().forEach((track) => track.stop())
			this.mediaStream = null
			console.log("[WebRTCClient] Local media tracks stopped.")
		}

		if (this.peerConnection) {
			// Nullify event handlers
			// Explicitly remove tracks from senders to prevent "sender already has a track" errors
			this.peerConnection.getSenders().forEach((sender) => {
				if (sender.track) {
					try {
						this.peerConnection.removeTrack(sender)
					} catch (e) {
						console.warn(
							"[WebRTCClient] Error removing track from sender:",
							e
						)
					}
				}
			})
			this.peerConnection.ontrack = null
			this.peerConnection.onicecandidate = null
			this.peerConnection.oniceconnectionstatechange = null
			this.peerConnection.onconnectionstatechange = null
			this.peerConnection.ondatachannel = null

			if (this.dataChannel) {
				this.dataChannel.onopen = null
				this.dataChannel.onclose = null
				this.dataChannel.onmessage = null
				if (this.dataChannel.readyState !== "closed") {
					this.dataChannel.close()
				}
				this.dataChannel = null
			}
			if (this.peerConnection.signalingState !== "closed") {
				this.peerConnection.close()
			}
			this.peerConnection = null
			console.log("[WebRTCClient] PeerConnection closed.")
		}

		if (this.options.onDisconnected) {
			this.options.onDisconnected()
		}
		console.log("[WebRTCClient] Disconnected successfully.")
	}

	setMuted(muted) {
		if (this.mediaStream) {
			this.mediaStream.getAudioTracks().forEach((track) => {
				track.enabled = !muted
			})
			console.log(
				`[WebRTCClient] Microphone ${muted ? "muted" : "unmuted"}. Track enabled: ${!muted}`
			)
		} else {
			console.warn(
				"[WebRTCClient] Cannot set mute state: mediaStream is null."
			)
		}
	}

	sendTextData(message) {
		if (this.dataChannel && this.dataChannel.readyState === "open") {
			try {
				this.dataChannel.send(JSON.stringify(message))
				console.log("[WebRTCClient] Sent text data:", message)
			} catch (error) {
				console.error("[WebRTCClient] Error sending text data:", error)
			}
		} else {
			console.warn(
				"[WebRTCClient] Data channel not open, cannot send text data."
			)
		}
	}
}
