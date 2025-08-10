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
	IconMessagePlus,
	IconHeadphones,
	IconDots,
	IconAdjustments,
	IconLogout,
	IconX,
	IconDownload
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { motion, AnimatePresence } from "framer-motion"
import useClickOutside from "@hooks/useClickOutside"

const HelpVideoModal = ({ onClose }) => (
	<motion.div
		initial={{ opacity: 0 }}
		animate={{ opacity: 1 }}
		exit={{ opacity: 0 }}
		className="fixed inset-0 bg-black/70 backdrop-blur-md z-[100] flex items-center justify-center p-4"
		onClick={onClose}
	>
		<motion.div
			initial={{ scale: 0.9, y: 20 }}
			animate={{ scale: 1, y: 0 }}
			exit={{ scale: 0.9, y: -20 }}
			transition={{ duration: 0.2, ease: "easeInOut" }}
			onClick={(e) => e.stopPropagation()}
			className="relative bg-black p-2 rounded-xl shadow-2xl w-full max-w-3xl aspect-video border border-neutral-700"
		>
			<button
				onClick={onClose}
				className="absolute -top-3 -right-3 z-10 p-1.5 bg-neutral-800 text-white rounded-full hover:bg-neutral-700"
				aria-label="Close video"
			>
				<IconX size={18} />
			</button>
			<iframe
				className="w-full h-full rounded-lg"
				src="https://www.youtube.com/embed/wCmWFUX_ZrM?autoplay=1&rel=0&showinfo=0&controls=1"
				title="Sentient Demo Video"
				allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
				allowFullScreen
			></iframe>
		</motion.div>
	</motion.div>
)

const SidebarContent = ({
	isCollapsed,
	onToggle,
	onNotificationsOpen,
	onSearchOpen,
	unreadCount,
	isMobile = false,
	onMobileClose = () => {},
	installPrompt,
	handleInstallClick
}) => {
	const pathname = usePathname()
	const [userDetails, setUserDetails] = useState(null)
	const [isHelpModalOpen, setHelpModalOpen] = useState(false)
	const [isUserMenuOpen, setUserMenuOpen] = useState(false)
	const userMenuRef = useRef(null)

	useClickOutside(userMenuRef, () => setUserMenuOpen(false))

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
			<AnimatePresence>
				{isHelpModalOpen && (
					<HelpVideoModal onClose={() => setHelpModalOpen(false)} />
				)}
			</AnimatePresence>
			{/* Header */}
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

			{/* Search Button */}
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

			{/* Footer */}
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
										initial={{
											opacity: 0,
											y: 10,
											scale: 0.95
										}}
										animate={{ opacity: 1, y: 0, scale: 1 }}
										exit={{
											opacity: 0,
											y: 10,
											scale: 0.95
										}}
										className="absolute bottom-full right-0 mb-2 w-40 bg-neutral-900/80 backdrop-blur-md border border-neutral-700 rounded-lg shadow-lg p-1 z-50"
									>
										<Link
											href="/auth/logout"
											className="w-full flex items-center gap-2 text-left px-3 py-2 text-sm rounded-md text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-colors"
										>
											<IconLogout size={16} />
											<span>Logout</span>
										</Link>
									</motion.div>
								)}
							</AnimatePresence>
						</div>
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
	onSearchOpen,
	unreadCount,
	isMobileOpen,
	onMobileClose
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
		setInstallPrompt(null) // The prompt can only be used once.
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
				/>
			</motion.div>
		</>
	)
}
export default Sidebar
