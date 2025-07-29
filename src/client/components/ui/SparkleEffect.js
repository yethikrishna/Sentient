"use client"
import React, { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

const Sparkle = ({ x, y, rotation, size, delay }) => (
	<motion.div
		className="absolute"
		style={{
			left: `${x}%`,
			top: `${y}%`,
			width: size,
			height: size,
			rotate: rotation
		}}
		initial={{ scale: 0, opacity: 0 }}
		animate={{
			scale: [0, 1.2, 0.8, 1, 0],
			opacity: [0, 1, 1, 1, 0],
			transition: { duration: 0.8, delay, ease: "easeOut" }
		}}
	>
		<svg
			width="100%"
			height="100%"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
		>
			<path
				d="M12 2L14.09 8.26L20 9.27L15.55 13.97L16.91 20L12 16.9L7.09 20L8.45 13.97L4 9.27L9.91 8.26L12 2Z"
				fill="url(#sparkle-gradient)"
			/>
			<defs>
				<linearGradient
					id="sparkle-gradient"
					x1="12"
					y1="2"
					x2="12"
					y2="20"
					gradientUnits="userSpaceOnUse"
				>
					<stop stopColor="#FFC947" />
					<stop offset="1" stopColor="#00ADB5" />
				</linearGradient>
			</defs>
		</svg>
	</motion.div>
)

const SparkleEffect = ({ trigger }) => {
	const [sparkles, setSparkles] = useState([])

	useEffect(() => {
		if (trigger > 0) {
			const newSparkles = Array.from({ length: 15 }).map((_, i) => ({
				id: i + Math.random(),
				x: Math.random() * 100,
				y: Math.random() * 100,
				rotation: Math.random() * 360,
				size: Math.random() * 20 + 10,
				delay: Math.random() * 0.3
			}))
			setSparkles(newSparkles)
		}
	}, [trigger])

	return (
		<div className="absolute inset-0 pointer-events-none z-50">
			<AnimatePresence>
				{sparkles.map((sparkle) => (
					<Sparkle key={sparkle.id} {...sparkle} />
				))}
			</AnimatePresence>
		</div>
	)
}

export default SparkleEffect
