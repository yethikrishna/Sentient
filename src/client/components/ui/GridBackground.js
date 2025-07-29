import { cn } from "@utils/cn"
import React from "react"

export function GridBackground({ children, className }) {
	return (
		<div
			className={cn(
				"relative flex h-full w-full items-center justify-center bg-brand-black",
				className
			)}
		>
			<div
				className={cn(
					"absolute inset-0",
					"[background-size:40px_40px]",
					"[background-image:linear-gradient(to_right,#F1A21D20_1px,transparent_1px),linear-gradient(to_bottom,#F1A21D20_1px,transparent_1px)]"
				)}
			/>
			{/* Radial gradient for the container to give a faded look */}
			<div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-brand-black [mask-image:radial-gradient(ellipse_at_center,transparent_20%,black)]"></div>
			<div className="relative z-20">{children}</div>
		</div>
	)
}
