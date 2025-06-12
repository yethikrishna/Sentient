export class AudioPlayer {
	constructor(sampleRate = 24000) {
		// Safari requires a user gesture to start AudioContext, so we create it on the first chunk.
		this.audioContext = null;
		this.audioQueue = [];
		this.isPlaying = false;
		this.startTime = 0;
		this.sampleRate = sampleRate;
		console.log(`[AudioPlayer] Initialized for sample rate ${sampleRate}.`);
	}

	_initAudioContext() {
		if (!this.audioContext) {
			try {
				this.audioContext = new (window.AudioContext ||
					window.webkitAudioContext)({
					sampleRate: this.sampleRate
				});
				console.log(
					`[AudioPlayer] AudioContext created with sample rate: ${this.audioContext.sampleRate}`
				);
			} catch (e) {
				console.error("[AudioPlayer] Error creating AudioContext:", e);
			}
		}
	}

	addChunk(float32ArrayChunk) {
		if (!(float32ArrayChunk instanceof Float32Array)) {
			console.error(
				"[AudioPlayer] Invalid chunk received. Expected Float32Array."
			);
			return;
		}
		this.audioQueue.push(float32ArrayChunk);
		if (!this.isPlaying) {
			this.play();
		}
	}

	play() {
		this._initAudioContext(); // Ensure context exists
		if (
			!this.audioContext ||
			this.audioQueue.length === 0 ||
			this.isPlaying
		) {
			if (this.audioQueue.length === 0) {
				this.isPlaying = false; // Stop if queue is empty
			}
			return;
		}

		this.isPlaying = true;
		const chunk = this.audioQueue.shift();

		const buffer = this.audioContext.createBuffer(
			1,
			chunk.length,
			this.sampleRate
		);
		buffer.copyToChannel(chunk, 0);

		const source = this.audioContext.createBufferSource();
		source.buffer = buffer;
		source.connect(this.audioContext.destination);

		const scheduledTime =
			this.startTime > this.audioContext.currentTime
				? this.startTime
				: this.audioContext.currentTime;
		source.start(scheduledTime);
		this.startTime = scheduledTime + buffer.duration;

		source.onended = () => {
			// This is not perfectly synchronous, so we check the queue again
			if (this.audioQueue.length === 0) {
				this.isPlaying = false;
			} else {
				this.play();
			}
		};
	}

	stop() {
		this.audioQueue = [];
		this.isPlaying = false;
		this.startTime = 0;
		if (this.audioContext && this.audioContext.state !== "closed") {
			this.audioContext
				.close()
				.catch((e) =>
					console.error("[AudioPlayer] Error closing AudioContext:", e)
				);
		}
		this.audioContext = null; // Set to null to be recreated on next play
	}
}