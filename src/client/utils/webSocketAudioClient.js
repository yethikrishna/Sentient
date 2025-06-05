// src/client/utils/webSocketAudioClient.js
// Assume main server runs on port 5000 (from APP_SERVER_URL)
// and has a WebSocket endpoint at /ws/voice for audio.

// Helper function to convert Float32Array to Base64 string (remains same)
function float32ArrayToBase64(buffer) {
	let binary = ""
	const bytes = new Uint8Array(buffer.buffer)
	const len = bytes.byteLength
	for (let i = 0; i < len; i++) {
		binary += String.fromCharCode(bytes[i])
	}
	return window.btoa(binary)
}

// Helper function to convert Base64 string to Float32Array (remains same)
function base64ToFloat32Array(base64) {
	try {
		const binary_string = window.atob(base64)
		const len = binary_string.length
		const bytes = new Uint8Array(len)
		for (let i = 0; i < len; i++) {
			bytes[i] = binary_string.charCodeAt(i)
		}
		if (bytes.buffer.byteLength % 4 !== 0) {
			// console.warn("Received Base64 audio data with length not multiple of 4.");
		}
		return new Float32Array(bytes.buffer)
	} catch (e) {
		console.error("Error decoding Base64 to Float32Array:", e)
		return null
	}
}

export class WebSocketAudioClient {
	ws = null
	mediaStream = null
	audioContext = null
	sourceNode = null
	workletNode = null
	analyser = null 
	dataArray = null 
	animationFrameId = null 
	options = {}
	websocketId = null
	isConnected = false
	// MODIFIED: serverUrl now points to the main server's voice WebSocket endpoint.
	// This should ideally come from an environment variable (process.env.APP_SERVER_URL)
	// For now, hardcoding for demonstration, assuming APP_SERVER_URL is ws://localhost:5000
	serverUrl = `${(process.env.APP_SERVER_URL || "http://localhost:5000").replace(/^http/, "ws")}/ws/voice`


	constructor(options = {}) {
		this.options = options
		this.websocketId = "ws_client_" + Math.random().toString(36).substring(2, 9)
		console.log(`[WebSocketAudioClient] Initialized with ID: ${this.websocketId}. Server URL: ${this.serverUrl}`)
	}

	async connect() {
		if (this.isConnected || this.ws) {
			console.warn("[WebSocketAudioClient] Already connected or connecting.")
			return
		}
		console.log("[WebSocketAudioClient] Attempting to connect...")

		try {
			const constraints = { audio: { sampleRate: 16000, echoCancellation: true, noiseSuppression: true }, video: false }
			this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
			console.log("[WebSocketAudioClient] Got user media.")

			await this.setupAudioProcessing()

			this.ws = new WebSocket(this.serverUrl)
			this.setupWebSocketHandlers()
		} catch (error) {
			console.error("[WebSocketAudioClient] Connection setup error:", error)
			this.handleError(error instanceof Error ? error : new Error(String(error)))
			this.disconnect()
		}
	}

	async setupAudioProcessing() {
		if (!this.mediaStream) throw new Error("Media stream is not available.")
		if (this.audioContext) return

		try {
			this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
			console.log(`[WebSocketAudioClient] AudioContext sample rate: ${this.audioContext.sampleRate}`)

			// Ensure the audio-processor.js is in the public folder or accessible via this path
			const workletUrl = "/audio-processor.js";
			try {
				await this.audioContext.audioWorklet.addModule(workletUrl);
			} catch (e) {
				console.error(`[WebSocketAudioClient] Failed to load AudioWorklet from ${workletUrl}:`, e);
				throw new Error(`Failed to load AudioWorklet: ${e.message}. Ensure audio-processor.js is in the public directory.`);
			}

			this.workletNode = new AudioWorkletNode(this.audioContext, "audio-processor")
			this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream)
			this.sourceNode.connect(this.workletNode)
			// Do NOT connect workletNode to destination for sending audio to server.
			// this.workletNode.connect(this.audioContext.destination); // Only for local loopback/debug

			this.workletNode.port.onmessage = (event) => {
				if (this.ws && this.ws.readyState === WebSocket.OPEN) {
					const pcmFloat32Data = event.data // This is Float32Array from worklet
					// The server WebSocket /ws/voice now expects raw bytes.
					// Convert Float32Array to Int16Array then to bytes if server expects PCM16.
					// Or send Float32Array as bytes directly if server handles that.
					// For simplicity, sending Float32Array as raw bytes.
					this.ws.send(pcmFloat32Data.buffer); // Send the underlying ArrayBuffer
					// console.log(`[WebSocketAudioClient] Sent audio data (bytes: ${pcmFloat32Data.buffer.byteLength})`);
				}
			}
			console.log("[WebSocketAudioClient] AudioWorklet processing setup complete.")

			if (this.options.onAudioLevel) {
				this.analyser = this.audioContext.createAnalyser()
				this.analyser.fftSize = 256
				this.analyser.smoothingTimeConstant = 0.3
				this.sourceNode.connect(this.analyser)
				const bufferLength = this.analyser.frequencyBinCount
				this.dataArray = new Uint8Array(bufferLength)
				this.startAnalysisLoop()
			}
		} catch (error) {
			console.error("[WebSocketAudioClient] Error setting up audio processing:", error)
			throw new Error("Failed to setup audio processing.")
		}
	}

	setupWebSocketHandlers() {
		if (!this.ws) return

		this.ws.onopen = () => {
			console.log("[WebSocketAudioClient] WebSocket connection opened.")
			// Send initial auth message to the main server's WebSocket
			const token = localStorage.getItem("access_token"); // Or however you store client token
			if (token) {
				const authMessage = JSON.stringify({ type: "auth", token: token });
				this.ws?.send(authMessage);
				console.log("[WebSocketAudioClient] Sent auth message to main server WS.");
			} else {
				console.error("[WebSocketAudioClient] No access token found for WS auth.");
				this.ws?.close(1008, "Access token unavailable for WebSocket authentication.");
				return;
			}
			// this.isConnected = true; // Set isConnected after server confirms auth
			// if (this.options.onConnected) this.options.onConnected();
		}

		this.ws.onmessage = (event) => {
			if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
				// Handle binary audio data from server (dummy TTS)
				// Convert ArrayBuffer to Float32Array if that's what onAudioChunkReceived expects
				let audioChunk;
				if (event.data instanceof ArrayBuffer) {
					// Assuming server sends Float32 PCM directly as ArrayBuffer
					audioChunk = new Float32Array(event.data);
				} else if (event.data instanceof Blob) {
					// If server sends Blob, need to read it as ArrayBuffer first
					// This part is more complex and might need async handling for blob.arrayBuffer()
					console.warn("[WebSocketAudioClient] Received Blob audio, needs async processing.");
					// For simplicity, skipping blob processing here, ensure server sends ArrayBuffer or recognizable JSON
					return;
				}
				
				if (audioChunk && this.options.onAudioChunkReceived) {
					this.options.onAudioChunkReceived(audioChunk);
				}

			} else if (typeof event.data === 'string') {
				try {
					const data = JSON.parse(event.data)
					// console.log("[WebSocketAudioClient] Received JSON message:", data);
					if (data.type === "auth_success") {
						console.log(`[WebSocketAudioClient] WebSocket authenticated with server for user: ${data.user_id}.`);
						this.isConnected = true;
						if (this.options.onConnected) this.options.onConnected();
						if (this.audioContext && this.audioContext.state === "suspended") {
							this.audioContext.resume().then(() => console.log("[WebSocketAudioClient] AudioContext resumed."));
						}
					} else if (data.type === "auth_failure") {
						console.error(`[WebSocketAudioClient] WebSocket authentication failed: ${data.message}`);
						this.handleError(new Error(`Authentication failed: ${data.message}`));
						this.disconnect(); // Disconnect on auth failure
					} else if (data.type === "stt_result" && this.options.onTextMessage) {
                        this.options.onTextMessage(data); // Pass STT results if client wants them
                    } else if (data.type === "llm_response" && this.options.onTextMessage) {
                        this.options.onTextMessage(data); // Pass LLM text if client wants them
                    } else if (data.type === "tts_stream_end") {
						// Handle end of TTS stream if needed
						console.log("[WebSocketAudioClient] Received TTS stream end signal.");
					} else if (data.type === "pong"){
						// console.log("[WebSocketAudioClient] Received pong from server.");
					}
					// Handle other non-audio JSON messages if necessary
				} catch (e) {
					console.error("[WebSocketAudioClient] Error parsing received JSON message:", e, "Raw data:", event.data)
				}
			}
		}

		this.ws.onerror = (error) => {
			console.error("[WebSocketAudioClient] WebSocket error:", error)
			this.handleError(new Error("WebSocket connection error."))
		}

		this.ws.onclose = (event) => {
			console.log(`[WebSocketAudioClient] WebSocket closed: Code=${event.code}, Reason=${event.reason}`)
			this.isConnected = false
			if (this.options.onDisconnected) this.options.onDisconnected()
			this.cleanupAudioProcessing()
			this.ws = null
		}
	}

	// startAnalysisLoop, stopAnalysis, cleanupAudioProcessing, disconnect, setMuted, handleError remain largely the same
	// Ensure they correctly reference instance variables.

	startAnalysisLoop() {
        if (this.animationFrameId || !this.analyser || !this.dataArray || !this.options.onAudioLevel) return;
        let lastUpdateTime = 0;
        const throttleInterval = 100; // ms

        const analyze = () => {
            if (!this.analyser || !this.dataArray) { // Check if analyser still exists
                this.animationFrameId = null;
                return;
            }
            this.analyser.getByteFrequencyData(this.dataArray);
            const currentTime = performance.now();
            if (currentTime - lastUpdateTime > throttleInterval) {
                let sum = 0;
                for (let i = 0; i < this.dataArray.length; i++) {
                    sum += this.dataArray[i];
                }
                const averageLevel = sum / this.dataArray.length / 128.0; // Normalize to 0-1 range, 128 for Uint8
                this.options.onAudioLevel(Math.min(averageLevel * 1.5, 1.0)); // Amplify slightly, cap at 1
                lastUpdateTime = currentTime;
            }
            this.animationFrameId = requestAnimationFrame(analyze);
        };
        this.animationFrameId = requestAnimationFrame(analyze);
    }

    stopAnalysis() {
        if (this.animationFrameId !== null) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.analyser = null; // Release analyser
        this.dataArray = null;
    }

	cleanupAudioProcessing() {
        console.log("[WebSocketAudioClient] Cleaning up audio processing nodes...");
        this.stopAnalysis();

        if (this.workletNode) {
            this.workletNode.port.onmessage = null; // Remove listener
            this.workletNode.port.close();
            if (this.sourceNode) {
                try { this.sourceNode.disconnect(this.workletNode); } catch(e) { /* ignore */ }
            }
            try { this.workletNode.disconnect(); } catch(e) { /* ignore */ }
            this.workletNode = null;
        }
        if (this.sourceNode) {
            if (this.analyser) { // If analyser was connected
                try { this.sourceNode.disconnect(this.analyser); } catch(e) { /* ignore */ }
            }
            try { this.sourceNode.disconnect(); } catch(e) { /* ignore */ }
            this.sourceNode = null;
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close().then(() => console.log('[WebSocketAudioClient] AudioContext closed.'));
            this.audioContext = null;
        }
        console.log("[WebSocketAudioClient] Audio processing cleanup finished.");
    }

	disconnect() {
		console.log("[WebSocketAudioClient] Disconnecting...")
		this.cleanupAudioProcessing()

		if (this.ws) {
			this.ws.onopen = null; // Prevent handlers from firing on a closed socket
            this.ws.onmessage = null;
            this.ws.onerror = null;
            this.ws.onclose = null; 
			if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
                this.ws.close(1000, "Client disconnecting normally");
            }
			this.ws = null
		}

		this.isConnected = false
		if (this.options.onDisconnected) {
			this.options.onDisconnected()
		}
		console.log("[WebSocketAudioClient] Disconnected.")
	}

	setMuted(muted) {
		if (this.mediaStream) {
			this.mediaStream.getAudioTracks().forEach((track) => {
				track.enabled = !muted
			})
			console.log(`[WebSocketAudioClient] Mic track enabled: ${!muted}`)
		}
	}

	handleError(error) {
		console.error("[WebSocketAudioClient] Error:", error)
		if (this.options.onError) {
			this.options.onError(error)
		}
	}
}