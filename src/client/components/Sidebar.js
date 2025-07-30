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
	IconLayoutSidebarLeftCollapse,
	IconLayoutSidebarLeftExpand
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { motion, AnimatePresence } from "framer-motion"
import SidebarAnimation from "./SidebarAnimation"

const Sidebar = ({
	isCollapsed,
	onToggle,
	onNotificationsOpen,
	unreadCount
}) => {
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
			<motion.div
				animate={{ width: isCollapsed ? 80 : 256 }}
				transition={{ type: "spring", stiffness: 300, damping: 30 }}
				className="hidden md:flex fixed top-0 left-0 h-screen bg-brand-black border-r border-neutral-800/50 flex-col justify-between py-5 z-40"
			>
				<AnimatePresence>
					{!isCollapsed && (
						<motion.div
							initial={{ opacity: 0 }}
							animate={{ opacity: 1, transition: { delay: 0.2 } }}
							exit={{ opacity: 0 }}
							className="absolute inset-0 z-0"
						>
							<SidebarAnimation />
						</motion.div>
					)}
				</AnimatePresence>
				<div className="flex flex-col items-center gap-8 w-full relative z-10">
					<Link href="/chat">
						<img
							src="/images/half-logo-dark.svg"
							alt="Logo"
							className="w-8 h-8"
						/>
					</Link>
					<nav className="flex flex-col gap-2 w-full px-3">
						{navLinks.map((link) => {
							const isActive = pathname.startsWith(link.href)
							return (
								<Link
									href={link.href}
									key={link.title}
									className={cn(
										"flex items-center gap-4 rounded-lg p-3 transition-colors duration-200",
										isActive
											? "bg-brand-orange text-brand-black"
											: "text-neutral-400 hover:text-white hover:bg-neutral-800/50",
										isCollapsed && "justify-center"
									)}
								>
									{link.icon}
									{!isCollapsed && (
										<span className="font-semibold">
											{link.title}
										</span>
									)}
								</Link>
							)
						})}
						<button
							onClick={onNotificationsOpen}
							className={cn(
								"relative flex items-center gap-4 w-full p-3 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800/50",
								isCollapsed && "justify-center"
							)}
						>
							<IconBell size={28} />
							{!isCollapsed && (
								<span className="font-semibold">Activity</span>
							)}
							{unreadCount > 0 && (
								<motion.div
									initial={{ scale: 0 }}
									animate={{ scale: 1 }}
									className="absolute top-2 right-3 h-2.5 w-2.5 bg-red-500 rounded-full border-2 border-black"
								/>
							)}
						</button>
					</nav>
				</div>
				<div className="flex flex-col items-center gap-4 w-full px-3 relative z-10">
					<button
						onClick={onToggle}
						className={cn(
							"flex items-center gap-4 w-full p-3 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800/50",
							isCollapsed && "justify-center"
						)}
					>
						{isCollapsed ? (
							<IconLayoutSidebarLeftExpand size={28} />
						) : (
							<IconLayoutSidebarLeftCollapse size={28} />
						)}
						{!isCollapsed && (
							<span className="font-semibold">Collapse</span>
						)}
					</button>
					{!isSelfHost && (
						<Link
							href="/api/auth/logout"
							className={cn(
								"flex items-center gap-4 w-full p-3 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800/50",
								isCollapsed && "justify-center"
							)}
						>
							<IconLogout size={24} />
							{!isCollapsed && (
								<span className="font-semibold">Logout</span>
							)}
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
			</motion.div>
			{/* Mobile Bottom Navigation */}
			<div className="md:hidden fixed bottom-0 left-0 w-full bg-brand-black border-t border-neutral-800/50 z-40">
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
										? "text-brand-orange"
										: "text-neutral-400"
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
						className="relative flex flex-col items-center justify-center gap-1 w-full h-full transition-colors text-neutral-400"
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
