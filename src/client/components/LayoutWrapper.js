"use client"
import React, { useState, useEffect, useCallback } from "react"
import ChatOverlay from "@components/ChatOverlay"
import NotificationsOverlay from "@components/NotificationsOverlay"
import FloatingNav from "@components/FloatingNav"
import { usePathname, useRouter } from "next/navigation"
import { AnimatePresence, motion } from "framer-motion"
import CommandPalette from "./CommandPallete"

const Sparkle = ({ size, style, delay }) => (
	<motion.div
		style={{
			position: "absolute",
			width: size,
			height: size,
			backgroundColor: "white",
			borderRadius: "50%",
			...style
		}}
		initial={{ scale: 0, opacity: 0 }}
		animate={{ scale: [0, 1.2, 0], opacity: [0, 1, 0] }}
		transition={{
			duration: 1.5,
			repeat: Infinity,
			delay: delay,
			ease: "easeInOut"
		}}
	/>
)

const FloatingChatButton = ({ onClick }) => (
	<button
		onClick={onClick}
		className="fixed bottom-5 right-5 z-40 h-16 w-16 bg-gradient-to-br from-[var(--color-accent-blue)] to-blue-600 rounded-full shadow-lg flex items-center justify-center text-white pulse-glow-animation"
		aria-label="Open Chat"
	>
		<Sparkle size={4} style={{ top: "10%", left: "20%" }} delay={0} />
		<Sparkle size={3} style={{ top: "25%", left: "80%" }} delay={0.3} />
		<Sparkle size={2} style={{ top: "70%", left: "15%" }} delay={0.6} />
		<Sparkle size={4} style={{ top: "80%", left: "70%" }} delay={0.9} />
		<img src="/images/half-logo-dark.svg" alt="Chat" className="w-8 h-8" />
	</button>
)

export default function LayoutWrapper({ children }) {
	const [isChatOpen, setChatOpen] = useState(false)
	const [isNotificationsOpen, setNotificationsOpen] = useState(false)
	const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false)
	const pathname = usePathname()
	const router = useRouter()

	const handleChatOpen = useCallback(() => {
		setChatOpen(true)
	}, [])

	const handleNotificationsOpen = useCallback(() => {
		setNotificationsOpen(true)
	}, [])

	const showChatButton = pathname !== "/onboarding" && pathname !== "/"

	const handleKeyDown = useCallback(
		(e) => {
			if (e.ctrlKey) {
				switch (e.key.toLowerCase()) {
					case "h":
						router.push("/home")
						break
					case "j":
						router.push("/notes")
						break
					case "a":
						router.push("/tasks")
						break
					case "b":
						handleNotificationsOpen()
						break
					case "m":
						setChatOpen(true)
						break
					case "k":
						setCommandPaletteOpen((prev) => !prev)
						break
					default:
						return
				}
				e.preventDefault()
			} else if (e.key === "Escape") {
				if (isChatOpen) setChatOpen(false)
				if (isNotificationsOpen) setNotificationsOpen(false)
				if (isCommandPaletteOpen) setCommandPaletteOpen(false)
			}
		},
		[
			router,
			isChatOpen,
			isNotificationsOpen,
			isCommandPaletteOpen,
			handleNotificationsOpen
		]
	)

	useEffect(() => {
		window.addEventListener("keydown", handleKeyDown)
		return () => window.removeEventListener("keydown", handleKeyDown)
	}, [handleKeyDown])

	return (
		<>
			<FloatingNav
				onChatOpen={handleChatOpen}
				onNotificationsOpen={handleNotificationsOpen}
			/>
			<CommandPalette
				open={isCommandPaletteOpen}
				setOpen={setCommandPaletteOpen}
			/>
			{children}
			<AnimatePresence>
				{isChatOpen && (
					<ChatOverlay
						key="chat-overlay"
						onClose={() => setChatOpen(false)}
					/>
				)}
				{isNotificationsOpen && (
					<NotificationsOverlay
						key="notifications-overlay"
						onClose={() => setNotificationsOpen(false)}
					/>
				)}
			</AnimatePresence>
			{showChatButton &&
				!isChatOpen &&
				!isNotificationsOpen &&
				!isCommandPaletteOpen && (
					<FloatingChatButton onClick={handleChatOpen} />
				)}
		</>
	)
}
