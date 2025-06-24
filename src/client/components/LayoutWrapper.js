"use client"
import React, { useState } from "react"
import ChatOverlay from "@components/ChatOverlay"
import { IconMessage } from "@tabler/icons-react"

export default function LayoutWrapper({ children }) {
	const [isChatOpen, setChatOpen] = useState(false)

	return (
		<>
			{children}
			<ChatOverlay
				isOpen={isChatOpen}
				onClose={() => setChatOpen(false)}
			/>
			<button
				onClick={() => setChatOpen(true)}
				className="fixed bottom-8 right-8 bg-lightblue text-white w-16 h-16 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform duration-200 z-40"
				title="Open Chat"
			>
				<IconMessage size={32} />
			</button>
		</>
	)
}
