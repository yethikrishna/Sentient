"use client"
import React, { useState } from "react"
import ChatOverlay from "@components/ChatOverlay"
import { IconMessage } from "@tabler/icons-react"
import { usePathname } from "next/navigation"
import { AnimatePresence } from "framer-motion"

export default function LayoutWrapper({ children }) {
	const [isChatOpen, setChatOpen] = useState(false)
	const pathname = usePathname()

	const showChatButton = pathname !== "/onboarding"

	return (
		<>
			{children}
			<AnimatePresence>
				{isChatOpen && (
					<ChatOverlay onClose={() => setChatOpen(false)} />
				)}
			</AnimatePresence>
			{showChatButton && (
				<button
					onClick={() => setChatOpen(true)}
					className="fixed bottom-8 right-8 bg-darkblue border-5 border-lightblue text-white w-16 h-16 rounded-full flex items-center justify-center shadow-lg hover:bg-blue-500 hover:scale-110 transition-all duration-200 z-40"
					title="Open Chat"
				>
					<IconMessage size={32} />
				</button>
			)}
		</>
	)
}
