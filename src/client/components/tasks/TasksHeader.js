"use client"

import React, { useState, useEffect, useCallback } from "react"
import toast from "react-hot-toast"
import {
	IconList,
	IconCalendar,
	IconLayoutGrid, // This is This Month
	IconCalendarWeek, // This is This Week
	IconHelpCircle
} from "@tabler/icons-react"

const TasksHeader = ({ onOpenDemo }) => {
	const [userDetails, setUserDetails] = useState(null)

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) throw new Error("Failed to fetch user details")
			const result = await response.json()
			const userName =
				result?.data?.personalInfo?.name ||
				result?.data?.onboardingAnswers?.["user-name"]
			setUserDetails({ given_name: userName || "User" })
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
			setUserDetails({ given_name: "User" })
		}
	}, [])

	useEffect(() => {
		fetchUserDetails()
	}, [fetchUserDetails])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good Morning"
		if (hour < 18) return "Good Afternoon"
		return "Good Evening"
	}

	const viewOptions = [
		{ id: "all", icon: IconList, label: "All Tasks" },
		{ id: "week", icon: IconCalendarWeek, label: "This Week" },
		{ id: "month", icon: IconLayoutGrid, label: "This Month" }
	]

	return (
		<header className="flex flex-wrap items-center justify-between gap-4 px-4 sm:px-6 py-4 border-b border-[var(--color-primary-surface)] bg-[var(--color-primary-background)]">
			<h1 className="text-2xl sm:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-neutral-400 py-1">
				{getGreeting()}, {userDetails?.given_name || "User"}
			</h1>

			<div className="flex items-center gap-3 shrink-0">
				<button
					onClick={onOpenDemo}
					className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] bg-[var(--color-primary-surface)] hover:bg-[var(--color-primary-surface-elevated)] rounded-lg border border-[var(--color-primary-surface)] hover:border-[var(--color-accent-blue)] transition-all duration-200"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Interactive Walkthrough"
				>
					<IconHelpCircle size={16} />
					<span>Help</span>
				</button>
			</div>
		</header>
	)
}

export default TasksHeader
