"use client"
import React from "react"
import { motion } from "framer-motion"

const Shape = ({ className, initial, animate, transition }) => (
	<motion.div
		className={`absolute bg-brand-orange/10 blur-lg ${className}`}
		initial={initial}
		animate={animate}
		transition={transition}
	/>
)

const AnimatedBackground = () => {
	const shapes = [
		{
			className: "w-48 h-48 rounded-full",
			initial: { top: "10%", left: "15%", rotate: 0 },
			animate: { rotate: 360 },
			transition: { duration: 40, repeat: Infinity, ease: "linear" }
		},
		{
			className: "w-64 h-32 rounded-[50%]",
			initial: { top: "25%", left: "80%", y: 0 },
			animate: { y: [0, -30, 0] },
			transition: { duration: 10, repeat: Infinity, ease: "easeInOut" }
		},
		{
			className: "w-40 h-40 rounded-lg",
			initial: { top: "70%", left: "5%", rotate: 45 },
			animate: { rotate: 405 },
			transition: { duration: 50, repeat: Infinity, ease: "linear" }
		},
		{
			className: "w-32 h-56 rounded-full",
			initial: { top: "80%", left: "90%", x: 0 },
			animate: { x: [0, 20, 0] },
			transition: { duration: 8, repeat: Infinity, ease: "easeInOut" }
		},
		{
			className: "w-24 h-24 rounded-xl",
			initial: { top: "5%", left: "60%", rotate: 0 },
			animate: { rotate: -360 },
			transition: { duration: 60, repeat: Infinity, ease: "linear" }
		}
	]

	return (
		<div className="absolute inset-0 w-full h-full overflow-hidden">
			{shapes.map((shape, index) => (
				<Shape key={index} {...shape} />
			))}
		</div>
	)
}

export default AnimatedBackground
