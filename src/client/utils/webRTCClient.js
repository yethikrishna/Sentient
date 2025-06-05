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

	// MODIFIED: serverUrl to be configurable or use an environment variable
	// Defaulting to localhost:5000 for the main server, which should be set via APP_SERVER_URL
	// The actual path for the offer is /voice/offer on the main server
	signalingServerUrl = (process.env.APP_SERVER_URL || "http://localhost:5000") + "/voice/offer";


	constructor(options = {}) {
		this.options = options
		console.log(`[WebRTCClient] Initialized. Signaling server URL: ${this.signalingServerUrl}`);
	}

	async connect() {
		try {
			if (this.peerConnection && (this.peerConnection.connectionState === 'connected' || this.peerConnection.connectionState === 'connecting')) {
                console.warn('[WebRTCClient] Already connected or connecting.');
                return;
            }
			this.peerConnection = new RTCPeerConnection({
				iceServers: [{ urls: "stun:stun.l.google.com:19302" }] // Example STUN server
			});

			// Get user media
			try {
				this.mediaStream = await navigator.mediaDevices.getUserMedia({
					audio: true, // Request audio
					video: false // No video for voice chat
				})
				console.log("[WebRTCClient] Got user media.");
			} catch (mediaError) {
				console.error("[WebRTCClient] Media access error:", mediaError)
				if (this.options.onConnectError) {
					this.options.onConnectError(mediaError);
				}
				// Provide more specific error messages
				if (mediaError.name === "NotAllowedError") {
                    throw new Error("Microphone access denied. Please allow microphone access and try again.");
                } else if (mediaError.name === "NotFoundError") {
                    throw new Error("No microphone detected. Please connect a microphone and try again.");
                }
				throw mediaError // Re-throw original error if not handled
			}

			// Add local audio tracks to the peer connection
			this.mediaStream.getTracks().forEach((track) => {
				if (this.peerConnection) { // Check if peerConnection is not null
					this.peerConnection.addTrack(track, this.mediaStream)
				}
			})
			console.log("[WebRTCClient] Local tracks added to PeerConnection.");


			// Setup audio analysis for local mic level (optional)
			if (this.options.onAudioLevel && this.mediaStream) {
				this.setupAudioAnalysis(this.mediaStream)
			}

			// Handle incoming remote tracks (for receiving audio from server)
			this.peerConnection.addEventListener("track", (event) => {
				console.log("[WebRTCClient] Remote track received:", event.track, event.streams);
				if (this.options.onAudioStream && event.streams && event.streams[0]) {
					this.options.onAudioStream(event.streams[0])
				}
			})

			// Create a data channel for text messages (optional, if needed beyond audio)
			this.dataChannel = this.peerConnection.createDataChannel("textDataChannel")
			this.dataChannel.onopen = () => console.log("[WebRTCClient] Data channel opened.");
			this.dataChannel.onclose = () => console.log("[WebRTCClient] Data channel closed.");
			this.dataChannel.onmessage = (event) => {
				console.log("[WebRTCClient] Data channel message received:", event.data);
				if (this.options.onMessage) {
					this.options.onMessage(JSON.parse(event.data)); // Assuming JSON messages
				}
			};
			
			this.peerConnection.ondatachannel = (event) => {
                const receiveChannel = event.channel;
                console.log("[WebRTCClient] Remote data channel received:", receiveChannel.label);
                receiveChannel.onmessage = this.dataChannel.onmessage; // Reuse same handler
                receiveChannel.onopen = () => console.log(`[WebRTCClient] Remote data channel '${receiveChannel.label}' opened.`);
                receiveChannel.onclose = () => console.log(`[WebRTCClient] Remote data channel '${receiveChannel.label}' closed.`);
            };


			// Standard ICE candidate handling
            this.peerConnection.onicecandidate = async (event) => {
                if (event.candidate) {
                    // console.log('[WebRTCClient] New ICE candidate:', event.candidate);
                    // In a real scenario, you'd send this to the server via your signaling mechanism
                    // For dummy/simple HTTP signaling, often the offer/answer exchange handles this implicitly
                    // or requires a separate endpoint if candidates are trickled.
                } else {
                    // console.log('[WebRTCClient] All ICE candidates have been gathered.');
                }
            };

            this.peerConnection.oniceconnectionstatechange = () => {
                if (this.peerConnection) {
                    console.log('[WebRTCClient] ICE connection state change:', this.peerConnection.iceConnectionState);
                    if (this.peerConnection.iceConnectionState === 'failed' || 
                        this.peerConnection.iceConnectionState === 'disconnected' ||
                        this.peerConnection.iceConnectionState === 'closed') {
                        // Handle potential disconnection
                        // this.disconnect(); // Potentially call disconnect or a more specific error handler
						if (this.options.onConnectError) {
							this.options.onConnectError(new Error(`ICE connection state: ${this.peerConnection.iceConnectionState}`));
						}
                    }
                }
            };
			
			// Create and send offer
			const offer = await this.peerConnection.createOffer()
			await this.peerConnection.setLocalDescription(offer)
			console.log("[WebRTCClient] Offer created and local description set.");

			// Send offer to signaling server (main server)
			// MODIFIED: Use this.signalingServerUrl
			console.log(`[WebRTCClient] Sending offer to: ${this.signalingServerUrl}`);
			const response = await fetch(this.signalingServerUrl, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Accept: "application/json"
					// Authorization: `Bearer ${your_auth_token_if_needed}` // Add if your /voice/offer endpoint is protected
				},
				mode: "cors",
				body: JSON.stringify({
					sdp: offer.sdp,
					type: offer.type,
					webrtc_id: "client_" + Math.random().toString(36).substring(2, 9) // Optional client ID
				})
			})

			if (!response.ok) {
                const errorText = await response.text();
                console.error(`[WebRTCClient] Signaling server error: ${response.status} - ${errorText}`);
                throw new Error(`Signaling server request failed: ${response.status} - ${errorText}`);
            }

			const serverResponse = await response.json()
			console.log("[WebRTCClient] Received answer from server:", serverResponse);
			await this.peerConnection.setRemoteDescription(new RTCSessionDescription(serverResponse)) // Ensure it's an RTCSessionDescription
			console.log("[WebRTCClient] Remote description set.");


			if (this.options.onConnected) {
				this.options.onConnected()
			}
		} catch (error) {
			console.error("[WebRTCClient] Error connecting:", error)
			// Ensure disconnect is called to clean up resources
			this.disconnect() // Call disconnect on error
			if (this.options.onConnectError) { // Call the onConnectError callback
                this.options.onConnectError(error);
            }
			// Do not re-throw if onConnectError handles UI updates, otherwise:
			// throw error; 
		}
	}

	setupAudioAnalysis(streamToAnalyze) {
		if (!streamToAnalyze) {
			console.warn("[WebRTCClient] No stream provided for audio analysis.");
			return;
		}

		try {
			this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
			this.analyser = this.audioContext.createAnalyser()
			this.analyser.fftSize = 256 // Smaller FFT size for faster response, less detail
			this.analyser.smoothingTimeConstant = 0.3; // Some smoothing

			const source = this.audioContext.createMediaStreamSource(streamToAnalyze);
			source.connect(this.analyser)

			const bufferLength = this.analyser.frequencyBinCount
			this.dataArray = new Uint8Array(bufferLength)

			this.startAnalysisLoop()
			console.log("[WebRTCClient] Audio analysis setup complete for local mic.");
		} catch (error) {
			console.error("[WebRTCClient] Error setting up audio analysis:", error)
		}
	}

	startAnalysisLoop() {
		if (!this.analyser || !this.dataArray || !this.options.onAudioLevel) return;

		let lastUpdateTime = 0;
        const throttleInterval = 100; // Update UI every 100ms

		const analyze = () => {
			if (!this.analyser || !this.dataArray) { // Check if resources are still available
                this.animationFrameId = null;
                return;
            }
			this.analyser.getByteFrequencyData(this.dataArray); // Use frequency data for simplicity

			const currentTime = performance.now(); // More precise than Date.now() for animations
            if (currentTime - lastUpdateTime > throttleInterval) {
				let sum = 0;
				for (let i = 0; i < this.dataArray.length; i++) {
					sum += this.dataArray[i];
				}
				// Normalize to 0-1 range. Max value for Uint8Array elements is 255.
				// Average then scale.
				const average = sum / this.dataArray.length;
				const normalizedLevel = average / 128.0; // Crude normalization, 128 is half of 255
				
				// Apply some amplification and clamp
				const amplifiedLevel = Math.min(normalizedLevel * 1.5, 1.0); 

				this.options.onAudioLevel(amplifiedLevel);
				lastUpdateTime = currentTime;
			}
			this.animationFrameId = requestAnimationFrame(analyze);
		}
		this.animationFrameId = requestAnimationFrame(analyze);
	}

	stopAnalysis() {
		if (this.animationFrameId !== null) {
			cancelAnimationFrame(this.animationFrameId)
			this.animationFrameId = null
		}
		// Close AudioContext if it was created by this instance for analysis
        // Be careful if AudioContext is shared or used by other parts.
		if (this.audioContext && this.audioContext.state !== 'closed') {
			this.audioContext.close().then(() => {
				console.log("[WebRTCClient] AudioContext for analysis closed.");
			}).catch(e => console.error("[WebRTCClient] Error closing AudioContext:", e));
			this.audioContext = null;
		}
		this.analyser = null
		this.dataArray = null
	}

	disconnect() {
		console.log("[WebRTCClient] Disconnecting...");
		this.stopAnalysis()

		if (this.mediaStream) {
			this.mediaStream.getTracks().forEach((track) => track.stop())
			this.mediaStream = null
			console.log("[WebRTCClient] Local media tracks stopped.");
		}

		if (this.peerConnection) {
			this.peerConnection.onicecandidate = null;
            this.peerConnection.oniceconnectionstatechange = null;
            this.peerConnection.ontrack = null;
            this.peerConnection.ondatachannel = null;
			if (this.dataChannel) {
                this.dataChannel.onopen = null;
                this.dataChannel.onclose = null;
                this.dataChannel.onmessage = null;
                if (this.dataChannel.readyState !== 'closed') {
                    this.dataChannel.close();
                }
                this.dataChannel = null;
            }
			if (this.peerConnection.signalingState !== 'closed') {
                this.peerConnection.close();
            }
			this.peerConnection = null
			console.log("[WebRTCClient] PeerConnection closed.");
		}
		
		if (this.options.onDisconnected) {
			this.options.onDisconnected()
		}
		console.log("[WebRTCClient] Disconnected successfully.");
	}

	// The setMuted functionality is typically handled by enabling/disabling tracks on the mediaStream
    // The client (e.g., chat page) would call this.
    setMuted(muted) {
        if (this.mediaStream) {
            this.mediaStream.getAudioTracks().forEach(track => {
                track.enabled = !muted;
            });
            console.log(`[WebRTCClient] Microphone ${muted ? 'muted' : 'unmuted'}. Track enabled: ${!muted}`);
        }
    }

	sendTextData(message) {
        if (this.dataChannel && this.dataChannel.readyState === 'open') {
            try {
                this.dataChannel.send(JSON.stringify(message));
                console.log("[WebRTCClient] Sent text data:", message);
            } catch (error) {
                console.error("[WebRTCClient] Error sending text data:", error);
            }
        } else {
            console.warn("[WebRTCClient] Data channel not open, cannot send text data.");
        }
    }
}