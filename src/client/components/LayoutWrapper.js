"use client"
import React, { useState, useEffect } from "react"
import ChatOverlay from "@components/ChatOverlay"
import { IconMessage } from "@tabler/icons-react"
import Lenis from "lenis"

export default function LayoutWrapper({ children }) {
	const [isChatOpen, setChatOpen] = useState(false)

	useEffect(() => {
		const lenis = new Lenis()

		function raf(time) {
			lenis.raf(time)
			requestAnimationFrame(raf)
		}

		requestAnimationFrame(raf)
	}, [])

	return (
		<>
			{children}
			<ChatOverlay
				isOpen={isChatOpen}
				onClose={() => setChatOpen(false)}
			/>
			<button
				onClick={() => setChatOpen(true)}
				className="fixed bottom-8 right-8 bg-[var(--color-accent-blue)] text-white w-16 h-16 rounded-full flex items-center justify-center shadow-lg hover:bg-blue-500 hover:scale-110 transition-all duration-200 z-40"
				title="Open Chat"
			>
				<IconMessage size={32} />
			</button>
		</>
	)
}
