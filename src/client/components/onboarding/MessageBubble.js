"use client"
import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { IconSparkles, IconUser } from "@tabler/icons-react"

const MessageBubble = ({ text, sender }) => {
	const isAI = sender === "ai"

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 20, scale: 0.9 }}
			animate={{ opacity: 1, y: 0, scale: 1 }}
			transition={{ duration: 0.3, ease: "easeOut" }}
			className={cn(
				"w-full flex gap-4 items-start",
				!isAI && "justify-end"
			)}
		>
			{isAI && (
				<div className="w-10 h-10 flex-shrink-0 bg-brand-gray rounded-full flex items-center justify-center border-2 border-brand-orange/50">
					<IconSparkles className="text-brand-orange" />
				</div>
			)}
			<div
				className={cn(
					"max-w-xl p-4 rounded-2xl text-base",
					isAI
						? "bg-brand-gray rounded-tl-none text-brand-white"
						: "bg-brand-orange rounded-br-none text-brand-black font-medium"
				)}
			>
				{text}
			</div>
			{!isAI && (
				<div className="w-10 h-10 flex-shrink-0 bg-brand-gray rounded-full flex items-center justify-center border-2 border-brand-orange/50">
					<IconUser className="text-brand-orange" />
				</div>
			)}
		</motion.div>
	)
}

export default MessageBubble
