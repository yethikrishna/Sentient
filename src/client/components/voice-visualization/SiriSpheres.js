"use client"
import React, { useRef, useMemo, useState } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import * as THREE from "three"
import { Color } from "three"

const Ring = ({ color, initialRotation }) => {
	const ringRef = useRef()

	useFrame(({ clock }) => {
		if (ringRef.current) {
			const t = clock.getElapsedTime()
			// Apply a slow, continuous base rotation
			ringRef.current.rotation.x = initialRotation[0] + t * 0.1
			ringRef.current.rotation.y = initialRotation[1] + t * 0.2
			ringRef.current.rotation.z = initialRotation[2] + t * 0.15
		}
	})

	return (
		<mesh ref={ringRef}>
			<torusGeometry args={[1.2, 0.05, 32, 100]} />
			<meshPhysicalMaterial
				color={color}
				emissive={color}
				emissiveIntensity={0.3} // Reduced from 1.2 to prevent overexposure
				transmission={0}
				roughness={0.4}
				metalness={0.0}
				thickness={0}
				ior={1.0}
				transparent
				opacity={0.9} // Slightly transparent for better blending
			/>
		</mesh>
	)
}

const Scene = ({ status, audioLevel = 0 }) => {
	const groupRef = useRef()
	const [currentScale, setCurrentScale] = useState(1)
	const redColor = useMemo(() => new Color("#ff3b30"), [])
	const finalColors = useMemo(() => {
		const orange = new Color("#F1A21D") // brand-orange
		const blue = new Color("#4a9eff") // sentient-blue
		const green = new Color("#28A745") // brand-green
		return [orange, blue, green]
	}, [])

	const [ringColors, setRingColors] = useState(() => [
		new Color("#ff3b30"),
		new Color("#ff3b30"),
		new Color("#ff3b30")
	])

	useFrame(({ clock }) => {
		const t = clock.getElapsedTime()

		setRingColors((prevColors) => {
			const newColors = prevColors.map((color) => color.clone())

			if (status === "disconnected") {
				newColors.forEach((c) => c.copy(redColor))
			} else if (status === "connecting") {
				const colorFactor = (Math.sin(t * 3) + 1) / 2 // Slower oscillation
				newColors.forEach((c, i) => {
					c.lerpColors(redColor, finalColors[i], colorFactor)
				})
			} else if (status === "connected") {
				newColors.forEach((c, i) => {
					c.lerp(finalColors[i], 0.05) // Slower transition
				})
			}

			return newColors
		})

		// Scale logic
		let targetScale = 1
		if (status === "connecting") {
			targetScale = 1 + Math.sin(t * 4) * 0.2
		} else if (status === "connected") {
			// Clamp the audio level's effect to prevent excessive scaling
			targetScale = 1 + Math.min(audioLevel, 1.0) * 0.5
		}

		setCurrentScale((prevScale) => {
			const diff = targetScale - prevScale
			return prevScale + diff * 0.1 // Smooth interpolation
		})

		if (groupRef.current) {
			groupRef.current.scale.setScalar(currentScale)
		}
	})

	const ringConfigs = useMemo(
		() => [
			{ initialRotation: [Math.PI / 2, 0, 0] },
			{ initialRotation: [0, Math.PI / 2, Math.PI / 4] },
			{ initialRotation: [Math.PI / 4, Math.PI / 4, Math.PI / 2] }
		],
		[]
	)

	return (
		<>
			<ambientLight intensity={0.2} />
			<pointLight position={[5, 5, 5]} intensity={0.5} />
			<pointLight position={[-5, -5, -5]} intensity={0.3} />
			<group ref={groupRef}>
				{ringConfigs.map((config, i) => (
					<Ring
						key={i}
						color={ringColors[i]}
						initialRotation={config.initialRotation}
					/>
				))}
			</group>
		</>
	)
}

const SiriSpheres = ({ status, audioLevel = 0 }) => {
	return (
		<div className="absolute inset-0 z-10">
			<Canvas
				camera={{ position: [0, 0, 4], fov: 50 }}
				gl={{
					outputColorSpace: THREE.SRGBColorSpace,
					toneMapping: THREE.ACESFilmicToneMapping,
					toneMappingExposure: 1.0
				}}
			>
				<Scene status={status} audioLevel={audioLevel} />
			</Canvas>
		</div>
	)
}

export default SiriSpheres
