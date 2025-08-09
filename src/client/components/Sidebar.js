"use client"
import React, { useState, useEffect, useRef } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import {
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
	IconDots,
	IconAdjustments,
	IconLogout,
	IconX,
	IconDownload,
	IconHeadphones
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { motion, AnimatePresence } from "framer-motion"
import useClickOutside from "@hooks/useClickOutside"

const UserProfileSection = ({ isCollapsed, user }) => {
	const [isUserMenuOpen, setUserMenuOpen] = useState(false)
	const userMenuRef = useRef(null)
	useClickOutside(userMenuRef, () => setUserMenuOpen(false))

	// CHANGED: Use the environment variable for the namespace
	const roles =
		user?.[`${process.env.NEXT_PUBLIC_AUTH0_NAMESPACE}/roles`] || []
	const isPro = roles.includes("Pro")
	const planName = isPro ? "Pro" : "Basic"

	const dashboardUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL
		? `${process.env.NEXT_PUBLIC_LANDING_PAGE_URL}/dashboard`
		: "#"

	return (
		<div
			className={cn(
				"flex items-center justify-between bg-neutral-800/40 border border-neutral-700/80 rounded-lg p-1.5",
				isCollapsed && "flex-col gap-2"
			)}
		>
			<div
				className={cn(
					"flex items-center gap-2 p-1 rounded-md flex-grow",
					isCollapsed ? "w-full justify-center" : ""
				)}
			>
				{user?.picture ? (
					<img
						src={user.picture}
						alt="User"
						className="w-7 h-7 rounded-full flex-shrink-0"
					/>
				) : (
					<div className="w-7 h-7 rounded-full bg-neutral-700 flex items-center justify-center flex-shrink-0">
						<IconUser size={16} />
					</div>
				)}
				<AnimatePresence>
					{!isCollapsed && (
						<motion.div
							initial={{ opacity: 0, width: 0 }}
							animate={{ opacity: 1, width: "auto" }}
							exit={{ opacity: 0, width: 0 }}
							className="overflow-hidden whitespace-nowrap"
						>
							<p className="font-semibold text-sm text-white">
								{user?.name || "User"}
							</p>
							<span
								className={cn(
									"text-xs",
									isPro
										? "text-brand-orange"
										: "text-neutral-400"
								)}
							>
								{planName}
							</span>
						</motion.div>
					)}
				</AnimatePresence>
			</div>
			{!isCollapsed && (
				<div className="relative" ref={userMenuRef}>
					<button
						onClick={() => setUserMenuOpen(!isUserMenuOpen)}
						className="p-2 rounded-md hover:bg-neutral-700 text-neutral-400 hover:text-white"
					>
						<IconDots size={16} />
					</button>
					<AnimatePresence>
						{isUserMenuOpen && (
							<motion.div
								initial={{ opacity: 0, y: 10, scale: 0.95 }}
								animate={{ opacity: 1, y: 0, scale: 1 }}
								exit={{ opacity: 0, y: 10, scale: 0.95 }}
								className="absolute bottom-full right-0 mb-2 w-48 bg-neutral-900/80 backdrop-blur-md border border-neutral-700 rounded-lg shadow-lg p-1 z-50"
							>
								<a
									href={dashboardUrl}
									target="_blank"
									rel="noopener noreferrer"
									className="w-full flex items-center gap-2 text-left px-3 py-2 text-sm rounded-md text-neutral-200 hover:bg-neutral-700/50 transition-colors"
								>
									<IconAdjustments size={16} />
									<span>Account & Billing</span>
								</a>
								<a
									href="/api/auth/logout"
									className="w-full flex items-center gap-2 text-left px-3 py-2 text-sm rounded-md text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-colors"
								>
									<IconLogout size={16} />
									<span>Logout</span>
								</a>
							</motion.div>
						)}
					</AnimatePresence>
				</div>
			)}
		</div>
	)
}

const SidebarContent = ({
	isCollapsed,
	onToggle,
	onNotificationsOpen,
	onSearchOpen,
	unreadCount,
	isMobile = false,
	onMobileClose = () => {},
	installPrompt,
	handleInstallClick,
	user
}) => {
	const pathname = usePathname()
	const [isHelpModalOpen, setHelpModalOpen] = useState(false)

	// CHANGED: Use the environment variable for the namespace
	const roles =
		user?.[`${process.env.NEXT_PUBLIC_AUTH0_NAMESPACE}/roles`] || []
	const isPro = roles.includes("Pro")

	const dashboardUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL
		? `${process.env.NEXT_PUBLIC_LANDING_PAGE_URL}/dashboard`
		: "#"

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
			<AnimatePresence>
				{isHelpModalOpen && (
					<div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
						<div className="bg-neutral-800 p-6 rounded-lg text-center">
							<h3 className="text-lg font-bold mb-4">
								Help Video
							</h3>
							<p>Video player would be here.</p>
							<button
								onClick={() => setHelpModalOpen(false)}
								className="mt-4 px-4 py-2 bg-brand-orange text-black rounded"
							>
								Close
							</button>
						</div>
					</div>
				)}
			</AnimatePresence>
			<div
				className={cn(
					"flex items-center justify-between mb-4 px-2",
					isCollapsed && "justify-center"
				)}
			>
				<Link
					href="/chat"
					className="flex items-center gap-2"
					onClick={isMobile ? onMobileClose : undefined}
				>
					<img
						src="/images/half-logo-dark.svg"
						alt="Logo"
						className="w-7 h-7"
					/>
					<AnimatePresence>
						{!isCollapsed && (
							<motion.span className="font-bold text-lg text-white whitespace-nowrap">
								Sentient
							</motion.span>
						)}
					</AnimatePresence>
				</Link>
				<AnimatePresence>
					{isMobile && (
						<button
							onClick={onMobileClose}
							className="p-1.5 rounded-full hover:bg-neutral-800"
						>
							<IconX size={18} />
						</button>
					)}
				</AnimatePresence>
			</div>

			<button
				onClick={() => {
					onSearchOpen()
					if (isMobile) onMobileClose()
				}}
				className={cn(
					"w-full flex items-center gap-3 bg-neutral-800/40 border border-neutral-700/80 rounded-lg p-2.5 text-left mb-4 hover:bg-neutral-800/80 transition-colors",
					isCollapsed && "justify-center"
				)}
			>
				<IconSearch
					size={18}
					className="text-neutral-300 flex-shrink-0"
				/>
				{!isCollapsed && (
					<span className="text-sm font-medium text-neutral-200">
						Search...
					</span>
				)}
			</button>

			{!isPro && (
				<a
					href={dashboardUrl}
					target="_blank"
					rel="noopener noreferrer"
					className={cn(
						"w-full bg-neutral-800/40 border border-neutral-700/80 rounded-lg p-2.5 text-left mb-2 hover:bg-neutral-800/80 transition-colors",
						isCollapsed && "flex justify-center"
					)}
				>
					<div className="flex items-center gap-3">
						<div className="bg-neutral-700/80 p-1 rounded-full text-brand-orange">
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
										Unlock all features
									</p>
								</motion.div>
							)}
						</AnimatePresence>
					</div>
				</a>
			)}

			<nav className="flex flex-col gap-1 flex-grow overflow-hidden">
				{navLinks.map((link) => {
					const isActive = pathname.startsWith(link.href)
					return (
						<Link
							href={link.href}
							key={link.title}
							onClick={isMobile ? onMobileClose : undefined}
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

			<div className="flex flex-col gap-2">
				{installPrompt && (
					<button
						onClick={handleInstallClick}
						className={cn(
							"w-full flex items-center gap-3 bg-green-600/20 border border-green-500/50 text-green-300 rounded-lg p-2 text-left text-sm hover:bg-green-600/40 transition-colors",
							isCollapsed && "justify-center"
						)}
					>
						<IconDownload size={20} className="flex-shrink-0" />
						{!isCollapsed && (
							<span className="font-medium whitespace-nowrap">
								Install App
							</span>
						)}
					</button>
				)}
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
					onClick={() => setHelpModalOpen(true)}
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

				<UserProfileSection isCollapsed={isCollapsed} user={user} />
			</div>
		</div>
	)
}

const Sidebar = ({
	isCollapsed,
	onToggle,
	onNotificationsOpen,
	onSearchOpen,
	unreadCount,
	isMobileOpen,
	onMobileClose,
	user
}) => {
	const [installPrompt, setInstallPrompt] = useState(null)

	useEffect(() => {
		const handleBeforeInstallPrompt = (e) => {
			e.preventDefault()
			setInstallPrompt(e)
		}

		window.addEventListener(
			"beforeinstallprompt",
			handleBeforeInstallPrompt
		)

		return () => {
			window.removeEventListener(
				"beforeinstallprompt",
				handleBeforeInstallPrompt
			)
		}
	}, [])

	const handleInstallClick = async () => {
		if (!installPrompt) return
		const result = await installPrompt.prompt()
		console.log(`Install prompt was: ${result.outcome}`)
		setInstallPrompt(null)
	}

	return (
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
								onSearchOpen={onSearchOpen}
								unreadCount={unreadCount}
								isMobile={true}
								installPrompt={installPrompt}
								handleInstallClick={handleInstallClick}
								user={user}
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
					onSearchOpen={onSearchOpen}
					unreadCount={unreadCount}
					installPrompt={installPrompt}
					handleInstallClick={handleInstallClick}
					user={user}
				/>
			</motion.div>
		</>
	)
}
export default Sidebar
