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
		<header className="flex flex-wrap items-center justify-between gap-4 p-4 md:px-8 md:py-6 border-b border-[var(--color-primary-surface)] flex-shrink-0">
			<div className="flex items-center gap-6">
				<h1 className="text-3xl lg:text-4xl font-semibold text-white">
					{getGreeting()}, {userDetails?.given_name || "User"}
				</h1>
			</div>

			<div className="flex items-center gap-2 sm:gap-4">
				<button
					onClick={onOpenDemo}
					className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-white bg-sentient-blue/20 rounded-full border border-sentient-blue/50 pulse-glow-animation"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Interactive Walkthrough"
				>
					<IconHelpCircle size={18} />
					<span>Help</span>
				</button>
			</div>
		</header>
	)
}

export default TasksHeader
