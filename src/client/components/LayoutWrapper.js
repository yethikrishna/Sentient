"use client"
import React, { useState } from "react"
import ChatOverlay from "@components/ChatOverlay"
import FloatingNav from "@components/FloatingNav"
import { IconMessage } from "@tabler/icons-react"
import { usePathname } from "next/navigation"
import { AnimatePresence } from "framer-motion"

export default function LayoutWrapper({ children }) {
	const [isChatOpen, setChatOpen] = useState(false)
	const pathname = usePathname()

	const showChatButton = pathname !== "/onboarding" && pathname !== "/"

	return (
		<>
			<FloatingNav onChatOpen={() => setChatOpen(true)} />
			{children}
			<AnimatePresence>
				{isChatOpen && (
					<ChatOverlay onClose={() => setChatOpen(false)} />
				)}
			</AnimatePresence>
			{
				showChatButton && !isChatOpen && null // Button is now in FloatingNav, this logic might be repurposed or removed
			}
		</>
	)
}
