"use client"

import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { useState, useEffect } from "react"

const COLOR_VARIANTS = {
	primary: {
		border: [
			"border-emerald-500/60",
			"border-cyan-400/50",
			"border-slate-600/30"
		],
		gradient: "from-emerald-500/30"
	},
	secondary: {
		border: [
			"border-violet-500/60",
			"border-fuchsia-400/50",
			"border-slate-600/30"
		],
		gradient: "from-violet-500/30"
	},
	senary: {
		border: [
			"border-blue-500/60",
			"border-sky-400/50",
			"border-slate-600/30"
		],
		gradient: "from-blue-500/30"
	},
	octonary: {
		border: [
			"border-red-500/60",
			"border-rose-400/50",
			"border-slate-600/30"
		],
		gradient: "from-red-500/30"
	}
}

const AnimatedGrid = () => (
	<motion.div
		className="absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,transparent_30%,black)]"
		animate={{ backgroundPosition: ["0% 0%", "100% 100%"] }}
		transition={{
			duration: 40,
			repeat: Infinity,
			ease: "linear"
		}}
	>
		<div className="h-full w-full [background-image:repeating-linear-gradient(100deg,#64748B_0%,#64748B_1px,transparent_1px,transparent_4%)] opacity-20" />
	</motion.div>
)

export function BackgroundCircles({
	className,
	variant = "octonary",
	audioLevel = 0,
	isActive = false
}) {
	const variantStyles = COLOR_VARIANTS[variant]
	const [animationParams, setAnimationParams] = useState({
		scale: 1,
		duration: 5,
		intensity: 0
	})

	useEffect(() => {
		if (isActive && audioLevel > 0) {
			const enhancedLevel = Math.min(1, audioLevel * 1.5)
			setAnimationParams({
				scale: 1 + enhancedLevel * 0.3,
				duration: Math.max(2, 5 - enhancedLevel * 3),
				intensity: enhancedLevel
			})
		} else if (animationParams.intensity > 0) {
			const timer = setTimeout(
				() =>
					setAnimationParams({ scale: 1, duration: 5, intensity: 0 }),
				300
			)
			return () => clearTimeout(timer)
		}
	}, [audioLevel, isActive, animationParams.intensity])

	return (
		<div
			className={cn(
				"relative flex h-full w-full items-center justify-center overflow-hidden bg-transparent",
				className
			)}
		>
			<AnimatedGrid />
			<motion.div
				className="absolute h-[480px] w-[480px]"
				initial={{ opacity: 0, scale: 0.9 }}
				animate={{ opacity: 1, scale: 1 }}
				transition={{ duration: 1.5, delay: 0.3, ease: "easeOut" }}
			>
				{[0, 1, 2].map((i) => (
					<motion.div
						key={i}
						className={cn(
							"absolute inset-0 rounded-full",
							"border-2 bg-gradient-to-br to-transparent",
							variantStyles.border[i],
							variantStyles.gradient
						)}
						animate={{
							rotate: 360,
							scale: [
								1 + i * 0.05,
								(1 + i * 0.05) *
									(1 +
										(isActive
											? animationParams.intensity * 0.2
											: 0.02)),
								1 + i * 0.05
							],
							opacity: [
								0.7 + i * 0.1,
								0.8 +
									i * 0.1 +
									(isActive
										? animationParams.intensity * 0.2
										: 0),
								0.7 + i * 0.1
							]
						}}
						transition={{
							duration: isActive
								? animationParams.duration
								: 8 + i * 2,
							repeat: Infinity,
							ease: "easeInOut"
						}}
					/>
				))}
			</motion.div>
		</div>
	)
}
