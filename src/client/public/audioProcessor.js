class AudioProcessor extends AudioWorkletProcessor {
	// Buffer audio chunks until we have a desired size
	_bufferSize = 2048 // Send chunks of this size (adjust as needed)
	_bytesWritten = 0
	_buffer = new Float32Array(this._bufferSize)

	constructor() {
		super()
	}

	process(inputs, outputs, parameters) {
		// inputs[0][0] is the Float32Array of PCM data for the first channel
		const inputChannelData = inputs[0][0]

		if (!inputChannelData) {
			return true // Keep processor alive
		}

		// Append new data to buffer
		let dataToCopy = inputChannelData
		let spaceLeft = this._bufferSize - this._bytesWritten

		while (dataToCopy.length > 0) {
			const toCopyNow = dataToCopy.subarray(
				0,
				Math.min(dataToCopy.length, spaceLeft)
			)
			this._buffer.set(toCopyNow, this._bytesWritten)
			this._bytesWritten += toCopyNow.length

			if (this._bytesWritten >= this._bufferSize) {
				this.port.postMessage(this._buffer.slice(0))
				this._bytesWritten = 0
			}

			dataToCopy = dataToCopy.subarray(toCopyNow.length)
			spaceLeft = this._bufferSize - this._bytesWritten
		}

		return true
	}
}

registerProcessor("audio-processor", AudioProcessor)
