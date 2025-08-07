"use client"
import React, { useMemo } from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"

function TextShimmerComponent({
	children,
	as: Component = "span",
	className,
	duration = 2,
	spread = 2
}) {
	const MotionComponent = motion[Component]

	const dynamicSpread = useMemo(() => {
		return (children?.length || 0) * spread
	}, [children, spread])

	return (
		<MotionComponent
			className={cn(
				"relative inline-block bg-[length:250%_100%,auto] bg-clip-text",
				"text-transparent [--base-color:#a1a1aa] [--base-gradient-color:#000]",
				"[background-repeat:no-repeat,padding-box] [--bg:linear-gradient(90deg,#0000_calc(50%-var(--spread)),var(--base-gradient-color),#0000_calc(50%+var(--spread)))]",
				"dark:[--base-color:theme(colors.brand-white)] dark:[--base-gradient-color:theme(colors.brand-orange)] dark:[--bg:linear-gradient(90deg,#0000_calc(50%-var(--spread)),var(--base-gradient-color),#0000_calc(50%+var(--spread)))]",
				className
			)}
			initial={{ backgroundPosition: "100% center" }}
			animate={{ backgroundPosition: "0% center" }}
			transition={{
				repeat: Infinity,
				duration,
				ease: "linear"
			}}
			style={{
				"--spread": `${dynamicSpread}px`,
				backgroundImage: `var(--bg), linear-gradient(var(--base-color), var(--base-color))`
			}}
		>
			{children}
		</MotionComponent>
	)
}

export const TextShimmer = React.memo(TextShimmerComponent)
