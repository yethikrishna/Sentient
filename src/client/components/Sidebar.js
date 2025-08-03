"use client"
import React, { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import {
	IconAdjustments,
	IconChecklist,
	IconPlugConnected,
	IconUser,
	IconMessage,
	IconBell,
	IconBrain,
	IconSearch,
	IconLayoutSidebarLeftCollapse,
	IconLayoutSidebarLeftExpand,
	IconArrowUpCircle,
	IconMessagePlus,
	IconHeadphones,
	IconDots
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { motion, AnimatePresence } from "framer-motion"

const SidebarContent = ({
	isCollapsed,
	onToggle,
	onNotificationsOpen,
	unreadCount,
	isMobile = false,
	onMobileClose = () => {}
}) => {
	const pathname = usePathname()
	const [userDetails, setUserDetails] = useState(null)

	useEffect(() => {
		fetch("/api/user/profile")
			.then((res) => (res.ok ? res.json() : null))
			.then((data) => setUserDetails(data))
	}, [])

	const navLinks = [
		{ title: "Chat", href: "/chat", icon: <IconMessage size={20} /> },
		{ title: "Tasks", href: "/tasks", icon: <IconChecklist size={20} /> },
		{ title: "Memories", href: "/memories", icon: <IconBrain size={20} /> },
		{
			title: "Integrations",
			href: "/integrations",
			icon: <IconPlugConnected size={20} />
		},
		{
			title: "Settings",
			href: "/settings",
			icon: <IconAdjustments size={20} />
		}
	]

	return (
		<div className="flex flex-col h-full w-full overflow-y-auto custom-scrollbar">
			{/* Header */}
			<div
				className={cn(
					"flex items-center justify-between mb-4 px-2",
					isCollapsed && "justify-center"
				)}
			>
				<Link href="/chat" className="flex items-center gap-2">
					<img
						src="/images/half-logo-dark.svg"
						alt="Logo"
						className="w-7 h-7"
					/>
				</Link>
				<AnimatePresence>
					{!isCollapsed && (
						<motion.div
							initial={{ opacity: 0, x: -10 }}
							animate={{ opacity: 1, x: 0 }}
							exit={{ opacity: 0, x: -10 }}
							transition={{ duration: 0.2, delay: 0.1 }}
							className="flex items-center gap-1"
						>
							<button className="p-1.5 rounded-md hover:bg-neutral-800 text-neutral-400 hover:text-white">
								<IconSearch size={18} />
							</button>
						</motion.div>
					)}
				</AnimatePresence>
			</div>

			{/* Upgrade Button */}
			<button
				className={cn(
					"w-full bg-neutral-800/40 border border-neutral-700/80 rounded-lg p-2.5 text-left mb-2 hover:bg-neutral-800/80 transition-colors",
					isCollapsed && "flex justify-center"
				)}
			>
				<div className="flex items-center gap-3">
					<div className="bg-neutral-700/80 p-1 rounded-full">
						<IconArrowUpCircle size={18} />
					</div>
					<AnimatePresence>
						{!isCollapsed && (
							<motion.div
								initial={{ opacity: 0, width: 0 }}
								animate={{ opacity: 1, width: "auto" }}
								exit={{ opacity: 0, width: 0 }}
								className="overflow-hidden whitespace-nowrap"
							>
								<p className="font-semibold text-sm text-white">
									Upgrade to Pro
								</p>
								<p className="text-xs text-neutral-400">
									All features & unlimited usage
								</p>
							</motion.div>
						)}
					</AnimatePresence>
				</div>
			</button>

			{/* Main Navigation */}
			<nav className="flex flex-col gap-1 flex-grow overflow-hidden">
				{navLinks.map((link) => {
					const isActive = pathname.startsWith(link.href)
					return (
						<Link
							href={link.href}
							key={link.title}
							className={cn(
								"flex items-center gap-3 rounded-md p-2 transition-colors duration-200 text-sm",
								isActive
									? "text-white bg-neutral-800"
									: "text-neutral-400 hover:text-white hover:bg-neutral-800/50",
								isCollapsed && "justify-center"
							)}
						>
							{link.icon}
							{!isCollapsed && (
								<span className="font-medium whitespace-nowrap">
									{link.title}
								</span>
							)}
						</Link>
					)
				})}
				<hr className="border-neutral-800 my-2" />
			</nav>
			<button
				onClick={onNotificationsOpen}
				className={cn(
					"flex items-center gap-3 rounded-md p-2 transition-colors duration-200 text-sm relative",
					"text-neutral-400 hover:text-white hover:bg-neutral-800/50",
					isCollapsed && "justify-center"
				)}
			>
				<IconBell size={20} />
				{!isCollapsed && (
					<span className="font-medium">Notifications</span>
				)}
				{unreadCount > 0 && (
					<div className="absolute top-1.5 right-1.5 h-2 w-2 bg-red-500 rounded-full" />
				)}
			</button>

			{/* Footer */}
			<div className="flex flex-col gap-2">
				{isMobile ? (
					<button
						onClick={onMobileClose}
						className="flex items-center gap-3 rounded-md p-2 transition-colors duration-200 text-sm text-neutral-400 hover:text-white hover:bg-neutral-800/50"
					>
						<IconLayoutSidebarLeftCollapse size={20} />
						<span className="font-medium whitespace-nowrap">
							Collapse
						</span>
					</button>
				) : (
					<button
						onClick={onToggle}
						className={cn(
							"flex items-center gap-3 rounded-md p-2 transition-colors duration-200 text-sm",
							"text-neutral-400 hover:text-white hover:bg-neutral-800/50",
							isCollapsed && "justify-center"
						)}
					>
						{isCollapsed ? (
							<IconLayoutSidebarLeftExpand size={20} />
						) : (
							<IconLayoutSidebarLeftCollapse size={20} />
						)}
						{!isCollapsed && (
							<span className="font-medium whitespace-nowrap">
								Collapse
							</span>
						)}
					</button>
				)}
				<button
					className={cn(
						"w-full flex items-center gap-3 bg-neutral-800/40 border border-neutral-700/80 rounded-lg p-2 text-left text-sm hover:bg-neutral-800/80 transition-colors",
						isCollapsed && "justify-center"
					)}
				>
					<IconHeadphones
						size={20}
						className="text-neutral-400 flex-shrink-0"
					/>
					{!isCollapsed && (
						<span className="font-medium text-neutral-300 whitespace-nowrap">
							Need help?
						</span>
					)}
				</button>
				<div
					className={cn(
						"flex items-center justify-between bg-neutral-800/40 border border-neutral-700/80 rounded-lg p-1.5",
						isCollapsed && "flex-col gap-2"
					)}
				>
					<Link
						href="/settings"
						className={cn(
							"flex items-center gap-2 p-1 rounded-md hover:bg-neutral-800/80 flex-grow",
							isCollapsed ? "w-full justify-center" : ""
						)}
					>
						{userDetails?.picture ? (
							<img
								src={userDetails.picture}
								alt="User"
								className="w-7 h-7 rounded-full flex-shrink-0"
							/>
						) : (
							<div className="w-7 h-7 rounded-full bg-neutral-700 flex items-center justify-center flex-shrink-0">
								<IconUser size={16} />
							</div>
						)}
						{!isCollapsed && (
							<span className="font-semibold text-sm text-white whitespace-nowrap">
								{userDetails?.given_name || "User"}
							</span>
						)}
					</Link>
					{!isCollapsed && (
						<button className="p-2 rounded-md hover:bg-neutral-700 text-neutral-400 hover:text-white">
							<IconDots size={16} />
						</button>
					)}
				</div>
			</div>
		</div>
	)
}

const Sidebar = ({
	isCollapsed,
	onToggle,
	onNotificationsOpen,
	unreadCount,
	isMobileOpen,
	onMobileClose
}) => (
	<>
		{/* Mobile Sidebar */}
		<AnimatePresence>
			{isMobileOpen && (
				<>
					<motion.div
						className="fixed inset-0 bg-black/60 z-40 md:hidden"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						onClick={onMobileClose}
					/>
					<motion.div
						className="fixed top-0 left-0 h-screen w-[260px] bg-black p-3 text-neutral-200 border-r border-neutral-800/50 z-50 md:hidden"
						initial={{ x: "-100%" }}
						animate={{ x: 0 }}
						exit={{ x: "-100%" }}
						transition={{
							type: "spring",
							stiffness: 300,
							damping: 30
						}}
					>
						<SidebarContent
							isCollapsed={false}
							onMobileClose={onMobileClose}
							onNotificationsOpen={onNotificationsOpen}
							unreadCount={unreadCount}
							isMobile={true}
						/>
					</motion.div>
				</>
			)}
		</AnimatePresence>

		{/* Desktop Sidebar */}
		<motion.div
			animate={{ width: isCollapsed ? 80 : 260 }}
			transition={{ type: "spring", stiffness: 300, damping: 30 }}
			className="hidden md:flex fixed top-0 left-0 h-screen bg-black flex-col p-3 text-neutral-200 border-r border-neutral-800/50 z-40"
		>
			<SidebarContent
				isCollapsed={isCollapsed}
				onToggle={onToggle}
				onNotificationsOpen={onNotificationsOpen}
				unreadCount={unreadCount}
			/>
		</motion.div>
	</>
)
export default Sidebar
