"use client"

import { useEffect, useCallback } from "react"
import { usePathname, useRouter } from "next/navigation"

/**
 * Custom hook to manage global keyboard shortcuts.
 * It intelligently adds/removes listeners based on the current route.
 * @param {function} onNotificationsOpen - Callback to open notifications.
 * @param {function} onCommandPaletteToggle - Callback to toggle the command palette.
 */
export function useGlobalShortcuts(
	onNotificationsOpen,
	onCommandPaletteToggle
) {
	const router = useRouter()
	const pathname = usePathname()

	// Shortcuts are disabled on these routes
	const isDisabled = ["/", "/onboarding"].includes(pathname)

	const handleKeyDown = useCallback(
		(e) => {
			if (e.ctrlKey) {
				switch (e.key.toLowerCase()) {
					case "h":
						router.push("/home")
						break
					case "t":
						router.push("/tasks")
						break
					case "b":
						onNotificationsOpen()
						break
					case "k":
						onCommandPaletteToggle()
						break
					case "m":
						router.push("/home")
						break
					default:
						return
				}
				e.preventDefault()
			}
		},
		[router, onNotificationsOpen, onCommandPaletteToggle]
	)

	useEffect(() => {
		if (isDisabled) return

		window.addEventListener("keydown", handleKeyDown)
		return () => window.removeEventListener("keydown", handleKeyDown)
	}, [isDisabled, handleKeyDown])
}
