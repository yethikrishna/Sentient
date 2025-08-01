"use client"
import React, { useRef, useMemo } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { Color, TorusGeometry, MeshPhysicalMaterial } from "three"
import { motion } from "framer-motion"
import { useSpring, useTransform } from "framer-motion"

const Ring = ({ color, initialRotation, scale }) => {
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
		<motion.mesh ref={ringRef} scale={scale}>
			<torusGeometry args={[1.2, 0.05, 32, 100]} />
			<meshPhysicalMaterial
				color={color}
				transmission={0.9}
				roughness={0.1}
				metalness={0.2}
				thickness={0.2}
				ior={1.5}
				transparent
				opacity={0.8}
			/>
		</motion.mesh>
	)
}

const Scene = ({ status, audioLevel }) => {
	const audioLevelSpring = useSpring(audioLevel, {
		stiffness: 200,
		damping: 30,
		mass: 1
	})

	const baseScale = status === "connecting" ? 1.1 : 1
	const scale = useTransform(
		audioLevelSpring,
		[0, 1],
		[baseScale, baseScale * 1.5]
	)

	const redColor = useMemo(() => new Color("#ff3b30"), [])
	const finalColors = useMemo(
		() => [
			new Color("#007aff"), // Blue
			new Color("#34c759"), // Green
			new Color("#ff9500") // Orange
		],
		[]
	)

	const ringColors = useMemo(
		() => [new Color(), new Color(), new Color()],
		[]
	)

	useFrame(({ clock }) => {
		const t = clock.getElapsedTime()
		if (status === "disconnected") {
			ringColors.forEach((c) => c.lerp(redColor, 0.1))
		} else if (status === "connecting") {
			const colorFactor = (Math.sin(t * 4) + 1) / 2 // Oscillates between 0 and 1
			ringColors.forEach((c, i) =>
				c.lerpColors(redColor, finalColors[i], colorFactor)
			)
		} else {
			ringColors.forEach((c, i) => c.lerp(finalColors[i], 0.1))
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
			<ambientLight intensity={0.5} />
			<pointLight position={[5, 5, 5]} intensity={1} />
			<pointLight position={[-5, -5, -5]} intensity={0.5} />
			<group>
				{ringConfigs.map((config, i) => (
					<Ring
						key={i}
						color={ringColors[i]}
						initialRotation={config.initialRotation}
						scale={scale}
					/>
				))}
			</group>
		</>
	)
}

const SiriSpheres = ({ status, audioLevel = 0 }) => {
	return (
		<div className="absolute inset-0 z-10">
			<Canvas camera={{ position: [0, 0, 4], fov: 50 }}>
				<Scene status={status} audioLevel={audioLevel} />
			</Canvas>
		</div>
	)
}

export default SiriSpheres
