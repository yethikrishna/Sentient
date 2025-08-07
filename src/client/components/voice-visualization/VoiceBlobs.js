"use client"
import { useEffect, useRef, useState } from "react"
import { cn } from "@utils/cn"
import React from "react"

const COLOR_SETS = {
	disconnected: {
		"--first-color": "220, 40, 40",
		"--second-color": "250, 60, 60",
		"--third-color": "200, 30, 30",
		"--fourth-color": "240, 50, 50",
		"--fifth-color": "230, 45, 45"
	},
	connecting: {
		"--first-color": "255, 190, 0",
		"--second-color": "255, 160, 0",
		"--third-color": "255, 210, 50",
		"--fourth-color": "250, 170, 20",
		"--fifth-color": "255, 200, 30"
	},
	connected: {
		"--first-color": "30, 80, 200",
		"--second-color": "80, 30, 220",
		"--third-color": "50, 100, 250",
		"--fourth-color": "100, 50, 240",
		"--fifth-color": "40, 90, 230"
	}
}

export const VoiceBlobs = ({
	audioLevel = 0,
	isActive = false,
	isConnecting = false,
	className,
	containerClassName
}) => {
	const layerRefs = useRef([
		useRef(null),
		useRef(null),
		useRef(null),
		useRef(null),
		useRef(null)
	]).current

	const gradientBackgroundStart = "rgb(18, 18, 18)"
	const gradientBackgroundEnd = "rgb(18, 18, 18)"
	const size = "65%"
	const blendingValue = "hard-light"

	const currentColorMode = isConnecting
		? "connecting"
		: isActive
			? "connected"
			: "disconnected"

	useEffect(() => {
		const rootStyle = document.documentElement.style
		rootStyle.setProperty(
			"--gradient-background-start",
			gradientBackgroundStart
		)
		rootStyle.setProperty(
			"--gradient-background-end",
			gradientBackgroundEnd
		)
		rootStyle.setProperty("--vb-size", size)
		rootStyle.setProperty("--blending-value", blendingValue)

		const currentColors = COLOR_SETS[currentColorMode]
		Object.entries(currentColors).forEach(([key, value]) => {
			rootStyle.setProperty(key, value)
		})

		return () => {
			rootStyle.removeProperty("--gradient-background-start")
			rootStyle.removeProperty("--gradient-background-end")
			rootStyle.removeProperty("--vb-size")
			rootStyle.removeProperty("--blending-value")
			Object.keys(COLOR_SETS.disconnected).forEach((key) =>
				rootStyle.removeProperty(key)
			)
		}
	}, [
		currentColorMode,
		size,
		gradientBackgroundStart,
		gradientBackgroundEnd,
		blendingValue
	])

	useEffect(() => {
		let animationFrameId
		let time = 0
		const baseMovementSpeed = 0.003
		const ringingPulseSpeed = Math.PI * 1.5
		const ringingPulseAmplitude = 0.15

		const animate = () => {
			time += baseMovementSpeed

			const baseScale = 1.0
			const activeScaleMultiplier = 1.5
			const minActiveScale = 1.02

			let scaleFactor = baseScale

			if (isConnecting) {
				scaleFactor =
					baseScale +
					Math.sin(time * ringingPulseSpeed) * ringingPulseAmplitude
			} else if (isActive) {
				scaleFactor =
					minActiveScale + audioLevel * activeScaleMultiplier
			}

			scaleFactor = Math.max(
				0.8,
				Math.min(scaleFactor, baseScale + activeScaleMultiplier)
			)

			layerRefs.forEach((layer, index) => {
				if (layer.current) {
					const currentTransform = layer.current.style.transform
					const match = currentTransform.match(/scale\(([^)]+)\)/)
					const currentScale = match
						? parseFloat(match[1])
						: baseScale

					const smoothingFactor = 0.25
					const smoothedScaleFactor =
						currentScale +
						(scaleFactor - currentScale) * smoothingFactor

					const x =
						50 +
						15 * Math.sin(time * (1 + index * 0.3)) +
						10 * Math.cos(time * (2 + index * 0.5))
					const y =
						50 +
						15 * Math.cos(time * (1.5 + index * 0.3)) +
						10 * Math.sin(time * (2.5 + index * 0.5))

					layer.current.style.background = `radial-gradient(circle at ${x}% ${y}%, rgba(var(${layer.current.dataset.colorvar}), 0.8) 0%, rgba(var(${layer.current.dataset.colorvar}), 0) 50%) no-repeat`
					layer.current.style.transform = `scale(${smoothedScaleFactor})`
					layer.current.style.transition = "transform 0.08s ease-out"
				}
			})
			animationFrameId = requestAnimationFrame(animate)
		}

		animationFrameId = requestAnimationFrame(animate)

		return () => {
			cancelAnimationFrame(animationFrameId)
		}
	}, [audioLevel, isActive, isConnecting, layerRefs])

	const [isSafari, setIsSafari] = useState(false)
	useEffect(() => {
		if (typeof navigator !== "undefined") {
			setIsSafari(
				/^((?!chrome|android).)*safari/i.test(navigator.userAgent)
			)
		}
	}, [])

	const layerConfigs = [
		{ colorVarName: "--first-color", opacity: "100" },
		{ colorVarName: "--second-color", opacity: "100" },
		{ colorVarName: "--third-color", opacity: "100" },
		{ colorVarName: "--fourth-color", opacity: "70" },
		{ colorVarName: "--fifth-color", opacity: "100" }
	]

	return (
		<div
			className={cn(
				"relative h-full w-full overflow-hidden top-0 left-0",
				containerClassName
			)}
			style={{ zIndex: 0, opacity: 0.8 }}
		>
			<svg className="hidden">
				<defs>
					<filter id="blurMe">
						<feGaussianBlur
							in="SourceGraphic"
							stdDeviation="10"
							result="blur-sm"
						/>
						<feColorMatrix
							in="blur-sm"
							mode="matrix"
							values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -8"
							result="goo"
						/>
						<feBlend in="SourceGraphic" in2="goo" />
					</filter>
				</defs>
			</svg>
			<div
				className={cn(
					"gradients-container h-full w-full blur-lg relative",
					isSafari ? "blur-2xl" : "[filter:url(#blurMe)_blur(40px)]"
				)}
			>
				{layerConfigs.map((config, index) => (
					<div
						key={index}
						ref={layerRefs[index]}
						data-colorvar={config.colorVarName}
						className={`absolute [mix-blend-mode:var(--blending-value)] w-[var(--vb-size)] h-[var(--vb-size)] top-[calc(50%-var(--vb-size)/2)] left-[calc(50%-var(--vb-size)/2)] opacity-${config.opacity} transform scale-100`}
						style={{
							background: `radial-gradient(circle at 50% 50%, rgba(var(${config.colorVarName}), 0.8) 0%, rgba(var(${config.colorVarName}), 0) 50%) no-repeat`,
							transformOrigin: "center center"
						}}
					></div>
				))}
			</div>
		</div>
	)
}
