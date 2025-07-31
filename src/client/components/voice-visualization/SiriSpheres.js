"use client"
import React from "react"
import { motion, useSpring, useTransform } from "framer-motion"
import { cn } from "@utils/cn"

const Sphere = ({
	initial,
	animate,
	transition,
	className,
	style,
	...props
}) => (
	<motion.div
		className={cn(
			"absolute rounded-full mix-blend-plus-lighter border-2",
			className
		)}
		initial={initial}
		animate={animate}
		transition={transition}
		style={style}
		{...props}
	/>
)

const SiriSpheres = ({ status, audioLevel = 0 }) => {
	const springConfig = { stiffness: 100, damping: 20, mass: 1 }
	const audioLevelSpring = useSpring(audioLevel, springConfig)

	const scale = useTransform(
		audioLevelSpring,
		[0, 1],
		[1, 1.5] // Base scale to max scale
	)
	const saturate = useTransform(
		audioLevelSpring,
		[0, 1],
		[1, 2.5] // Base saturation to max saturation
	)

	const sphereStyle = {
		scale,
		filter: `saturate(${saturate.get()})`
	}

	const spheres = [
		{
			id: 1,
			className: "bg-blue-500/10 border-blue-400/50",
			size: 200,
			disconnected: {
				x: [-20, 20, -20],
				y: [30, -30, 30],
				transition: {
					duration: 10,
					repeat: Infinity,
					repeatType: "mirror",
					ease: "easeInOut"
				}
			},
			connecting: {
				scale: [1, 1.1, 1],
				transition: {
					duration: 1.5,
					repeat: Infinity,
					ease: "easeInOut"
				}
			}
		},
		{
			id: 2,
			className: "bg-green-500/10 border-green-400/50",
			size: 250,
			disconnected: {
				x: [50, -50, 50],
				y: [-50, 50, -50],
				transition: {
					duration: 12,
					repeat: Infinity,
					repeatType: "mirror",
					ease: "easeInOut"
				}
			},
			connecting: {
				scale: [1, 1.05, 1],
				transition: {
					duration: 1.8,
					repeat: Infinity,
					ease: "easeInOut",
					delay: 0.2
				}
			}
		},
		{
			id: 3,
			className: "bg-purple-500/10 border-purple-400/50",
			size: 180,
			disconnected: {
				x: [-40, 40, -40],
				y: [40, -40, 40],
				transition: {
					duration: 15,
					repeat: Infinity,
					repeatType: "mirror",
					ease: "easeInOut"
				}
			},
			connecting: {
				scale: [1, 1.15, 1],
				transition: {
					duration: 1.3,
					repeat: Infinity,
					ease: "easeInOut",
					delay: 0.4
				}
			}
		}
	]

	const getAnimationProps = (sphere) => {
		switch (status) {
			case "connecting":
				return sphere.connecting
			case "connected":
				return {} // Style is handled by useSpring
			case "disconnected":
			default:
				return sphere.disconnected
		}
	}

	return (
		<div className="relative w-96 h-96 flex items-center justify-center">
			{spheres.map((sphere) => (
				<Sphere
					key={sphere.id}
					className={sphere.className}
					style={{
						width: sphere.size,
						height: sphere.size,
						...(status === "connected" && sphereStyle)
					}}
					animate={getAnimationProps(sphere)}
				/>
			))}
		</div>
	)
}

export default SiriSpheres
