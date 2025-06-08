// src/client/utils/webRTCClient.js
// src/client/utils/webRTCClient.js
export class WebRTCClient {
	peerConnection = null
	mediaStream = null
	dataChannel = null
	options
	audioContext = null
	analyser = null
	dataArray = null
	animationFrameId = null
	selectedAudioInputDeviceId = null // Store the selected device ID

	signalingServerUrl =
		(process.env.NEXT_PUBLIC_APP_SERVER_URL || "http://localhost:5000") +
		"/voice/offer"

	constructor(options = {}) {
		this.options = options
		console.log(
			`[WebRTCClient] Initialized. Signaling server URL: ${this.signalingServerUrl}`
		)
	}

	async connect(deviceId = null) {
		// Accept deviceId
		try {
			if (
				this.peerConnection &&
				(this.peerConnection.connectionState === "connected" ||
					this.peerConnection.connectionState === "connecting")
			) {
				console.warn("[WebRTCClient] Already connected or connecting.")
				return
			}
			this.selectedAudioInputDeviceId = deviceId // Store for potential use
			console.log(
				`[WebRTCClient] Attempting to connect using deviceId: ${deviceId || "default"}`
			)

			this.peerConnection = new RTCPeerConnection({
				iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
			})

			try {
				// Use the selected deviceId if provided
				const constraints = {
					audio: deviceId
						? {
								deviceId: { exact: deviceId },
								sampleRate: 16000,
								echoCancellation: true,
								noiseSuppression: true
							}
						: {
								sampleRate: 16000,
								echoCancellation: true,
								noiseSuppression: true
							},
					video: false
				}
				this.mediaStream =
					await navigator.mediaDevices.getUserMedia(constraints)
				console.log(
					"[WebRTCClient] Got user media with constraints:",
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
				throw mediaError
			}

			this.mediaStream.getTracks().forEach((track) => {
				if (this.peerConnection) {
					this.peerConnection.addTrack(track, this.mediaStream)
				}
			})
			console.log("[WebRTCClient] Local tracks added to PeerConnection.")

			if (this.options.onAudioLevel && this.mediaStream) {
				this.setupAudioAnalysis(this.mediaStream)
			}

			this.peerConnection.addEventListener("track", (event) => {
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
			})

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
					this.options.onMessage(JSON.parse(event.data))
				}
			}

			this.peerConnection.ondatachannel = (event) => {
				const receiveChannel = event.channel
				console.log(
					"[WebRTCClient] Remote data channel received:",
					receiveChannel.label
				)
				receiveChannel.onmessage = this.dataChannel.onmessage
				receiveChannel.onopen = () =>
					console.log(
						`[WebRTCClient] Remote data channel '${receiveChannel.label}' opened.`
					)
				receiveChannel.onclose = () =>
					console.log(
						`[WebRTCClient] Remote data channel '${receiveChannel.label}' closed.`
					)
			}

			this.peerConnection.onicecandidate = async (event) => {
				if (event.candidate) {
					// console.log('[WebRTCClient] New ICE candidate:', event.candidate);
				} else {
					// console.log('[WebRTCClient] All ICE candidates have been gathered.');
				}
			}

			this.peerConnection.oniceconnectionstatechange = () => {
				if (this.peerConnection) {
					console.log(
						"[WebRTCClient] ICE connection state change:",
						this.peerConnection.iceConnectionState
					)
					if (
						this.peerConnection.iceConnectionState === "failed" ||
						this.peerConnection.iceConnectionState ===
							"disconnected" ||
						this.peerConnection.iceConnectionState === "closed"
					) {
						if (this.options.onConnectError) {
							this.options.onConnectError(
								new Error(
									`ICE connection state: ${this.peerConnection.iceConnectionState}`
								)
							)
						}
					}
				}
			}

			const offer = await this.peerConnection.createOffer()
			await this.peerConnection.setLocalDescription(offer)
			console.log(
				"[WebRTCClient] Offer created and local description set."
			)

			console.log(
				`[WebRTCClient] Sending offer to: ${this.signalingServerUrl}`
			)
			const response = await fetch(this.signalingServerUrl, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Accept: "application/json"
				},
				mode: "cors",
				body: JSON.stringify({
					sdp: offer.sdp,
					type: offer.type,
					webrtc_id:
						"client_" + Math.random().toString(36).substring(2, 9)
				})
			})

			if (!response.ok) {
				const errorText = await response.text()
				console.error(
					`[WebRTCClient] Signaling server error: ${response.status} - ${errorText}`
				)
				throw new Error(
					`Signaling server request failed: ${response.status} - ${errorText}`
				)
			}

			const serverResponse = await response.json()
			console.log(
				"[WebRTCClient] Received answer from server:",
				serverResponse
			)
			await this.peerConnection.setRemoteDescription(
				new RTCSessionDescription(serverResponse)
			)
			console.log("[WebRTCClient] Remote description set.")

			if (this.options.onConnected) {
				this.options.onConnected()
			}
		} catch (error) {
			console.error("[WebRTCClient] Error connecting:", error)
			this.disconnect()
			if (this.options.onConnectError) {
				this.options.onConnectError(error)
			}
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
			this.analyser.fftSize = 256
			this.analyser.smoothingTimeConstant = 0.3

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
		const throttleInterval = 100

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
				const normalizedLevel = average / 128.0

				const amplifiedLevel = Math.min(normalizedLevel * 1.5, 1.0)

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
				.then(() => {
					console.log(
						"[WebRTCClient] AudioContext for analysis closed."
					)
				})
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
			this.peerConnection.onicecandidate = null
			this.peerConnection.oniceconnectionstatechange = null
			this.peerConnection.ontrack = null
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
