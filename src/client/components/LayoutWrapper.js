"use client"
import React, { useState, useEffect, useCallback } from "react"
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

export default function LayoutWrapper({ children }) {
	const [isNotificationsOpen, setNotificationsOpen] = useState(false)
	const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false)
	const pathname = usePathname()
	const router = useRouter()

	const handleNotificationsOpen = useCallback(() => {
		setNotificationsOpen(true)
	}, [])

	const handleKeyDown = useCallback(
		(e) => {
			if (e.ctrlKey) {
				switch (e.key.toLowerCase()) {
					case "h":
						router.push("/home")
						break
					case "a":
						router.push("/tasks")
						break
					case "b":
						handleNotificationsOpen()
						break
					case "k":
						setCommandPaletteOpen((prev) => !prev)
						break
					default:
						return
				}
				e.preventDefault()
			} else if (e.key === "Escape") {
				if (isNotificationsOpen) setNotificationsOpen(false)
				if (isCommandPaletteOpen) setCommandPaletteOpen(false)
			}
		},
		[
			router,
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
			<FloatingNav onNotificationsOpen={handleNotificationsOpen} />
			<CommandPalette
				open={isCommandPaletteOpen}
				setOpen={setCommandPaletteOpen}
			/>
			{children}
			<AnimatePresence>
				{isNotificationsOpen && (
					<NotificationsOverlay
						key="notifications-overlay"
						onClose={() => setNotificationsOpen(false)}
					/>
				)}
			</AnimatePresence>
		</>
	)
}
