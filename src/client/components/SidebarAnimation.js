"use client"
import React, { useMemo } from "react"
import { motion } from "framer-motion"

const Particle = ({ x, y, size, duration, delay }) => {
	return (
		<motion.div
			className="absolute rounded-full bg-brand-orange/30"
			style={{
				left: `${x}%`,
				top: `${y}%`,
				width: size,
				height: size
			}}
			animate={{
				x: [0, Math.random() * 20 - 10, 0], // Gentle horizontal drift
				y: [0, Math.random() * 20 - 10, 0], // Gentle vertical drift
				opacity: [0, 0.8, 0]
			}}
			transition={{
				duration,
				delay,
				repeat: Infinity,
				repeatType: "mirror",
				ease: "easeInOut"
			}}
		/>
	)
}

const SidebarAnimation = () => {
	const particleCount = 20

	// useMemo to prevent re-calculating particles on every render
	const particles = useMemo(() => {
		return Array.from({ length: particleCount }).map((_, i) => ({
			id: i,
			x: Math.random() * 100,
			y: Math.random() * 100,
			size: Math.random() * 3 + 1, // size between 1px and 4px
			duration: Math.random() * 5 + 5, // duration between 5s and 10s
			delay: Math.random() * 5
		}))
	}, [particleCount])

	return (
		<div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
			{/* Animated Gradient Background */}
			<motion.div
				className="absolute inset-0"
				animate={{
					background: [
						"linear-gradient(to bottom, transparent 50%, rgba(241, 162, 29, 0.1) 100%)",
						"linear-gradient(to bottom, transparent 40%, rgba(241, 162, 29, 0.15) 100%)",
						"linear-gradient(to bottom, transparent 50%, rgba(241, 162, 29, 0.1) 100%)"
					]
				}}
				transition={{
					duration: 12,
					repeat: Infinity,
					repeatType: "mirror",
					ease: "easeInOut"
				}}
			/>

			{/* Particles */}
			{particles.map((p) => (
				<Particle key={p.id} {...p} />
			))}
		</div>
	)
}

export default SidebarAnimation
