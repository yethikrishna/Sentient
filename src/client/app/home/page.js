"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import Sidebar from "@components/Sidebar"
import {
	IconBook,
	IconChecklist,
	IconMenu2,
	IconSparkles,
	IconTrendingUp
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { motion, useMotionValue, useTransform, useSpring } from "framer-motion"

const ActionCard = ({
	title,
	description,
	icon,
	href,
	accentColor = "blue"
}) => {
	const router = useRouter()
	const ref = useRef(null)

	const x = useMotionValue(0)
	const y = useMotionValue(0)

	const mouseXSpring = useSpring(x)
	const mouseYSpring = useSpring(y)

	const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ["6deg", "-6deg"])
	const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ["-6deg", "6deg"])

	const accentColors = {
		blue: "#4a9eff",
		green: "#00c851",
		purple: "#9c27b0",
		orange: "#ff8800"
	}

	const handleMouseMove = (e) => {
		if (!ref.current) return

		const rect = ref.current.getBoundingClientRect()
		const width = rect.width
		const height = rect.height
		const mouseX = e.clientX - rect.left
		const mouseY = e.clientY - rect.top
		const xPct = mouseX / width - 0.5
		const yPct = mouseY / height - 0.5

		x.set(xPct)
		y.set(yPct)
	}

	const handleMouseLeave = () => {
		x.set(0)
		y.set(0)
	}

	return (
		<motion.div
			ref={ref}
			onMouseMove={handleMouseMove}
			onMouseLeave={handleMouseLeave}
			onClick={() => router.push(href)}
			whileHover={{ scale: 1.02 }}
			whileTap={{ scale: 0.98 }}
			style={{
				rotateY,
				rotateX,
				transformStyle: "preserve-3d"
			}}
			className="bg-[var(--color-primary-surface)] rounded-lg border border-[var(--color-primary-surface-elevated)] p-6 lg:p-8 cursor-pointer hover:border-[var(--accent-color)] transition-all duration-300 relative group"
		>
			{/* Subtle glow effect on hover */}
			<div
				className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-20 transition-opacity duration-300 bg-gradient-to-r from-transparent via-[var(--accent-color)] to-transparent"
				style={{ "--accent-color": accentColors[accentColor] }}
			/>

			<div
				style={{
					transform: "translateZ(30px)",
					transformStyle: "preserve-3d"
				}}
				className="flex flex-col items-start text-left relative z-10"
			>
				<div className="mb-4 p-3 rounded-lg bg-[var(--color-primary-surface-elevated)] group-hover:bg-[var(--accent-color)] group-hover:bg-opacity-10 transition-colors duration-300">
					{React.cloneElement(icon, {
						className: `w-6 h-6 text-[var(--accent-color)]`,
						style: { "--accent-color": accentColors[accentColor] }
					})}
				</div>
				<h2 className="text-xl lg:text-2xl font-semibold text-[var(--color-text-primary)] mb-3">
					{title}
				</h2>
				<p className="text-[#b0b0b0] text-sm lg:text-base leading-relaxed">
					{description}
				</p>

				{/* Action indicator */}
				<div
					className="mt-4 flex items-center text-[var(--accent-color)] text-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300"
					style={{ "--accent-color": accentColors[accentColor] }}
				>
					<span>Get started</span>
					<svg
						className="w-4 h-4 ml-2 transform group-hover:translate-x-1 transition-transform duration-300"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M9 5l7 7-7 7"
						/>
					</svg>
				</div>
			</div>
		</motion.div>
	)
}

const StatsCard = ({ label, value, trend, trendDirection = "up" }) => (
	<motion.div
		initial={{ opacity: 0, y: 20 }}
		animate={{ opacity: 1, y: 0 }}
		className="bg-[var(--color-primary-surface)] rounded-lg border border-[var(--color-primary-surface-elevated)] p-4 lg:p-6"
	>
		<div className="flex items-center justify-between">
			<div>
				<p className="text-[var(--color-text-muted)] text-sm font-medium">
					{label}
				</p>
				<p className="text-[var(--color-text-primary)] text-2xl font-semibold mt-1">
					{value}
				</p>
			</div>
			{trend && (
				<div
					className={`flex items-center text-sm ${trendDirection === "up" ? "text-[var(--color-accent-green)]" : "text-[var(--color-accent-orange)]"}`}
				>
					<IconTrendingUp
						className={`w-4 h-4 mr-1 ${trendDirection === "down" ? "rotate-180" : ""}`}
					/>
					{trend}
				</div>
			)}
		</div>
	</motion.div>
)

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user details")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
		}
	}, [])

	useEffect(() => {
		fetchUserDetails()
	}, [fetchUserDetails])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good morning"
		if (hour < 18) return "Good afternoon"
		return "Good evening"
	}

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)]">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 border-b border-[var(--color-primary-surface)] md:hidden">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-[var(--color-text-primary)] hover:text-[var(--color-accent-blue)] transition-colors duration-150"
					>
						<IconMenu2 />
					</button>
				</header>
				<main className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar flex items-center justify-center">
					<div className="max-w-6xl w-full">
						{/* Header Section */}
						<div className="mb-8 lg:mb-12">
							<motion.div
								initial={{ opacity: 0, y: 20 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.5 }}
								className="flex items-center mb-3"
							>
								<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)]">
									{getGreeting()},{" "}
									{userDetails?.given_name || "User"}
								</h1>
								<IconSparkles className="w-6 h-6 text-[var(--color-accent-blue)] ml-3 animate-pulse" />
							</motion.div>
							<motion.p
								initial={{ opacity: 0, y: 20 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.5, delay: 0.1 }}
								className="text-lg text-[var(--color-text-secondary)]"
							>
								Ready to make today productive? Choose your
								focus area.
							</motion.p>
						</div>

						{/* Quick Stats -- (PENDING) PLACEHOLDER, ADD BACKEND LOGIC*/}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.2 }}
							className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 lg:mb-12"
						>
							<StatsCard
								label="Today's Tasks"
								value="5"
								trend="+2"
							/>
							<StatsCard
								label="Completed"
								value="12"
								trend="+8"
							/>
							<StatsCard
								label="Journal Entries"
								value="3"
								trend="+1"
							/>
							<StatsCard
								label="Streak"
								value="7 days"
								trend="+1 day"
							/>
						</motion.div>

						{/* Main Actions -- (PENDING) ADD PREVIEWS HERE. PREVIEW TODAY'S TASKS AND TODAY'S JOURNAL ITEMS */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.3 }}
							className="mb-8"
						>
							<h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-6">
								Quick Actions
							</h2>
							<div
								className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8"
								style={{ perspective: "1000px" }}
							>
								<ActionCard
									title="Journal"
									description="Reflect on your thoughts, capture insights, and track your personal growth journey."
									icon={<IconBook />}
									href="/journal"
									accentColor="purple"
								/>
								<ActionCard
									title="Tasks"
									description="Organize your workflow, manage projects, and stay on top of your daily commitments."
									icon={<IconChecklist />}
									href="/tasks"
									accentColor="blue"
								/>
							</div>
						</motion.div>
					</div>
				</main>
			</div>
		</div>
	)
}

export default HomePage
