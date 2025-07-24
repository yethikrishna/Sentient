"use client"
import React, { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import { FloatingDock } from "@components/ui/floating-dock"
import {
	IconAdjustments,
	IconChecklist,
	IconHome,
	IconLogout,
	IconPlugConnected
} from "@tabler/icons-react"

export default function FloatingNav() {
	const pathname = usePathname()
	const [userDetails, setUserDetails] = useState(null)
	const isSelfHost = process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"

	useEffect(() => {
		fetch("/api/user/profile")
			.then((res) => {
				if (res.ok) return res.json()
				return null
			})
			.then((data) => setUserDetails(data))
			.catch((err) => console.error("Failed to fetch user profile", err))
	}, [])

	const navLinks = [
		{
			title: "Chat",
			href: "/home",
			icon: (
				<IconHome className="h-full w-full text-neutral-500 dark:text-neutral-300" />
			)
		},
		{
			title: "Tasks",
			href: "/tasks",
			icon: (
				<IconChecklist className="h-full w-full text-neutral-500 dark:text-neutral-300" />
			)
		},
		{
			title: "Integrations",
			href: "/integrations",
			icon: (
				<IconPlugConnected className="h-full w-full text-neutral-500 dark:text-neutral-300" />
			)
		},
		{
			title: "Settings",
			href: "/settings",
			icon: (
				<IconAdjustments className="h-full w-full text-neutral-500 dark:text-neutral-300" />
			)
		}
	]

	const allLinks = [...navLinks]

	if (userDetails && !isSelfHost) {
		allLinks.push({
			title: "Logout",
			href: "/auth/logout",
			icon: (
				<IconLogout className="h-full w-full text-neutral-500 dark:text-neutral-300" />
			)
		})
	}

	if (pathname === "/onboarding" || pathname === "/") {
		return null
	}

	// Filter out the "Profile" link and replace it with "Settings"
	const finalLinks = allLinks.filter((link) => link.title !== "Profile")

	return <FloatingDock items={finalLinks} />
}
