export class WebRTCClient {
	constructor(options = {}) {
		this.peerConnection = null
		this.mediaStream = null
		this.dataChannel = null
		this.options = options
		this.audioContext = null
		this.analyser = null
		this.dataArray = null
		this.animationFrameId = null
		this.serverUrl =
			process.env.NEXT_PUBLIC_APP_SERVER_URL || "http://localhost:5000"
	}

	async connect(deviceId, authToken, rtcToken) {

		console.log("Connecting WebRTC client with deviceId:", deviceId)

		console.log("Using authToken:", authToken)
		console.log("Using rtcToken:", rtcToken)

		if (!authToken) {
			throw new Error("Authentication token is required to connect.")
		}
		if (!rtcToken) {
			throw new Error("RTC token is required to connect.")
		}

		console.log("Using server URL:", this.serverUrl)

		try {
			this.peerConnection = new RTCPeerConnection()

			console.log("Created RTCPeerConnection:", this.peerConnection)

			this.peerConnection.onicecandidate = (event) => {
				if (event.candidate) {
					console.log("ICE Candidate Found:", event.candidate)
				} else {
					console.log("All ICE candidates have been gathered.")
				}
			}

			this.peerConnection.oniceconnectionstatechange = (event) => {
				const state = this.peerConnection.iceConnectionState
				console.log(
					`%cICE Connection State Change: ${state}`,
					"font-weight: bold; color: blue;"
				)
				if (state === "failed") {
					console.error(
						"ICE connection failed. This often indicates a network or firewall issue."
					)
				}
			}

			this.peerConnection.onconnectionstatechange = (event) => {
				const state = this.peerConnection.connectionState
				console.log(
					`%cPeer Connection State Change: ${state}`,
					"font-weight: bold; color: green;"
				)
				if (state === "failed") {
					console.error(
						"Peer connection failed. The connection could not be established or has been lost."
					)
				}
			}

			this.peerConnection.ondatachannel = (event) => {
				console.log(
					"Data Channel established by remote peer:",
					event.channel
				)
			}

			const audioConstraints = deviceId
				? { deviceId: { exact: deviceId } }
				: true
			this.mediaStream = await navigator.mediaDevices.getUserMedia({
				audio: audioConstraints
			})

			this.setupAudioAnalysis()

			console.log("Acquired media stream:", this.mediaStream)

			this.mediaStream.getTracks().forEach((track) => {
				console.log("Adding track to peer connection:", track)
				// FIX: Add a null check before calling addTrack.
				// This prevents a crash if a previous connection was closed.
				if (this.peerConnection) {
					this.peerConnection.addTrack(track, this.mediaStream)
				}
			})

			this.peerConnection.addEventListener("track", (event) => {
				console.log("Received track event:", event)
				this.options.onAudioStream?.(event.streams[0])
			})

			this.dataChannel = this.peerConnection.createDataChannel("events")
			this.dataChannel.addEventListener("message", (event) => {
				try {
					const message = JSON.parse(event.data)
					this.options.onEvent?.(message)
				} catch (error) {
					console.error("Error parsing data channel message:", error)
				}
			})

			const offer = await this.peerConnection.createOffer()
			await this.peerConnection.setLocalDescription(offer)

			const response = await fetch(
				`${this.serverUrl}/voice/webrtc/offer`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						// Add this line to authenticate the request
						Authorization: `Bearer ${authToken}`
					},
					body: JSON.stringify({
						sdp: offer.sdp,
						type: offer.type,
						webrtc_id: rtcToken
					})
				}
			)

			if (!response.ok) {
				const errorText = await response.text()
				throw new Error(
					`Server responded with ${response.status}: ${errorText}`
				)
			}

			const serverResponse = await response.json()
			console.log("Received server response:", serverResponse)
			await this.peerConnection.setRemoteDescription(serverResponse)

			console.log("WebRTC connection established successfully.")

			this.options.onConnected?.()

			console.log("Setting up audio analysis.")
		} catch (error) {
			console.error("Error connecting WebRTC:", error)
			this.disconnect()
			throw error
		}
	}

	setupAudioAnalysis() {
		console.log("Setting up audio analysis with mediaStream:", this.mediaStream)
		if (!this.mediaStream || !this.options.onAudioLevel) return
		try {
			this.audioContext = new (window.AudioContext ||
				window.webkitAudioContext)()
			this.analyser = this.audioContext.createAnalyser()
			this.analyser.fftSize = 256
			const source = this.audioContext.createMediaStreamSource(
				this.mediaStream
			)
			source.connect(this.analyser)
			const bufferLength = this.analyser.frequencyBinCount
			this.dataArray = new Uint8Array(bufferLength)
			this.startAnalysis()
		} catch (error) {
			console.error("Error setting up audio analysis:", error)
		}
	}

	startAnalysis() {
		if (!this.analyser || !this.dataArray || !this.options.onAudioLevel)
			return
		let lastUpdateTime = 0
		const throttleInterval = 100 // 100ms

		const analyze = () => {
			if (!this.analyser || !this.dataArray) return
			this.analyser.getByteFrequencyData(this.dataArray)
			const currentTime = Date.now()
			if (currentTime - lastUpdateTime > throttleInterval) {
				let sum = 0
				for (let i = 0; i < this.dataArray.length; i++) {
					sum += this.dataArray[i]
				}
				const average = sum / this.dataArray.length / 255
				this.options.onAudioLevel(average)
				lastUpdateTime = currentTime
			}
			this.animationFrameId = requestAnimationFrame(analyze)
		}
		this.animationFrameId = requestAnimationFrame(analyze)
	}

	stopAnalysis() {
		if (this.animationFrameId) {
			cancelAnimationFrame(this.animationFrameId)
			this.animationFrameId = null
		}
		if (this.audioContext) {
			this.audioContext.close().catch(console.error)
			this.audioContext = null
		}
		this.analyser = null
		this.dataArray = null
	}

	disconnect() {
		this.stopAnalysis()
		this.mediaStream?.getTracks().forEach((track) => track.stop())
		this.mediaStream = null
		this.peerConnection?.close()
		this.peerConnection = null
		this.dataChannel = null
		this.options.onDisconnected?.()
	}
}
