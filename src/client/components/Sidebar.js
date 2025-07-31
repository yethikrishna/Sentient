"use client"
import React, { useState, useEffect, cloneElement } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import {
	IconAdjustments,
	IconChecklist,
	IconLogout,
	IconPlugConnected,
	IconUser,
	IconMessage,
	IconBell,
	IconBrain
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { motion } from "framer-motion"

const Sidebar = ({ onNotificationsOpen, unreadCount }) => {
	const pathname = usePathname()
	const [userDetails, setUserDetails] = useState(null)
	const isSelfHost = process.env.NEXT_PUBLIC_ENVIRONMENT === "selfhost"
	useEffect(() => {
		fetch("/api/user/profile")
			.then((res) => (res.ok ? res.json() : null))
			.then((data) => setUserDetails(data))
	}, [])
	const navLinks = [
		{ title: "Chat", href: "/chat", icon: <IconMessage size={28} /> },
		{ title: "Tasks", href: "/tasks", icon: <IconChecklist size={28} /> },
		{ title: "Memories", href: "/memories", icon: <IconBrain size={28} /> },
		{
			title: "Integrations",
			href: "/integrations",
			icon: <IconPlugConnected size={28} />
		},
		{
			title: "Settings",
			href: "/settings",
			icon: <IconAdjustments size={28} />
		}
	]
	return (
		<>
			{/* Desktop Sidebar */}
			<div className="hidden md:flex fixed top-0 left-0 h-screen w-20 bg-black border-r border-neutral-800/50 flex-col items-center justify-between py-5 z-40">
				<div className="flex flex-col items-center gap-8 w-full">
					<Link href="/chat">
						<img
							src="/images/half-logo-dark.svg"
							alt="Logo"
							className="w-8 h-8"
						/>
					</Link>
					<nav className="flex flex-col items-center gap-2 w-full">
						{navLinks.map((link) => {
							const isActive = pathname.startsWith(link.href)
							return (
								<Link
									href={link.href}
									key={link.title}
									className={cn(
										"flex flex-col items-center gap-1.5 transition-colors duration-200 w-full py-3",
										isActive
											? "text-white bg-neutral-800 border-r-2 border-white"
											: "text-neutral-400 hover:text-white hover:bg-neutral-800/50"
									)}
								>
									{link.icon}
									<span className="text-xs font-medium">
										{link.title}
									</span>
								</Link>
							)
						})}
						<button
							onClick={onNotificationsOpen}
							className="relative flex flex-col items-center gap-1.5 transition-colors duration-200 w-full py-3 text-neutral-400 hover:text-white hover:bg-neutral-800/50"
						>
							<IconBell size={28} />
							<span className="text-xs font-medium">
								Activity
							</span>
							{unreadCount > 0 && (
								<motion.div
									initial={{ scale: 0 }}
									animate={{ scale: 1 }}
									className="absolute top-2 right-5 h-2.5 w-2.5 bg-red-500 rounded-full border-2 border-black"
								/>
							)}
						</button>
					</nav>
				</div>
				<div className="flex flex-col items-center gap-4">
					{!isSelfHost && (
						<Link
							href="/api/auth/logout"
							className="flex flex-col items-center gap-1.5 text-neutral-400 hover:text-white transition-colors"
						>
							<IconLogout size={24} />
						</Link>
					)}
					<Link href="/settings">
						{userDetails?.picture ? (
							<img
								src={userDetails.picture}
								alt="User"
								className="w-9 h-9 rounded-full border-2 border-neutral-700"
							/>
						) : (
							<div className="w-9 h-9 rounded-full bg-neutral-800 flex items-center justify-center border-2 border-neutral-700">
								<IconUser className="w-5 h-5 text-white" />
							</div>
						)}
					</Link>
				</div>
			</div>
			{/* Mobile Bottom Navigation */}
			<div className="md:hidden fixed bottom-0 left-0 w-full bg-black border-t border-neutral-800/50 z-40">
				<nav className="flex items-center justify-around w-full h-16">
					{navLinks.map((link) => {
						const isActive = pathname.startsWith(link.href)
						return (
							<Link
								href={link.href}
								key={link.title}
								className={cn(
									"flex flex-col items-center justify-center gap-1 w-full h-full transition-colors",
									isActive
										? "text-white"
										: "text-neutral-400 hover:text-white"
								)}
							>
								{cloneElement(link.icon, { size: 24 })}
								<span className="text-xs font-medium">
									{link.title}
								</span>
							</Link>
						)
					})}
					<button
						onClick={onNotificationsOpen}
						className="relative flex flex-col items-center justify-center gap-1 w-full h-full transition-colors text-neutral-400 hover:text-white"
					>
						<IconBell size={24} />
						<span className="text-xs font-medium">Activity</span>
						{unreadCount > 0 && (
							<motion.div
								initial={{ scale: 0 }}
								animate={{ scale: 1 }}
								className="absolute top-2 right-1/2 translate-x-3 h-2.5 w-2.5 bg-red-500 rounded-full border-2 border-black"
							/>
						)}
					</button>
				</nav>
			</div>
		</>
	)
}
export default Sidebar
