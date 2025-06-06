// src/client/app/settings/page.js
"use client"

import { useState, useEffect, useCallback } from "react"
import Sidebar from "@components/Sidebar"
import toast from "react-hot-toast"
import ModalDialog from "@components/ModalDialog"
import {
	IconGift,
	IconRocket,
	IconMail,
	IconCalendarEvent,
	IconWorldSearch,
	IconLoader,
	IconSettingsCog
} from "@tabler/icons-react"
import React from "react"
import { Switch } from "@radix-ui/react-switch"
import { cn } from "@utils/cn"

const dataSourceIcons = {
	gmail: IconMail,
	gcalendar: IconCalendarEvent,
	internet_search: IconWorldSearch
}

const Settings = () => {
	const [userDetails, setUserDetails] = useState({})
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [pricing, setPricing] = useState("free")
	const [showReferralDialog, setShowReferralDialog] = useState(false)
	const [referralCode, setReferralCode] = useState("DUMMY")
	const [referrerStatus, setReferrerStatus] = useState(false)
	const [dataSources, setDataSources] = useState([])
	const [togglingSource, setTogglingSource] = useState(null)

	const fetchDataSources = useCallback(async () => {
		console.log("Fetching data sources...")
		try {
			const response = await fetch("/api/settings/data-sources")
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to fetch data sources")
			}
			const sourcesWithIcons = (
				Array.isArray(data.data_sources) ? data.data_sources : []
			).map((ds) => ({
				...ds,
				icon: dataSourceIcons[ds.name] || IconSettingsCog
			}))
			setDataSources(sourcesWithIcons)
			console.log("Data sources fetched:", sourcesWithIcons)
		} catch (error) {
			console.error("Error fetching data sources:", error)
			toast.error(`Error fetching data sources: ${error.message}`)
			setDataSources([])
		}
	}, [])

	const handleToggle = async (sourceName, enabled) => {
		console.log(`Toggling ${sourceName} to ${enabled}`)
		setTogglingSource(sourceName)

		const originalDataSources = JSON.parse(JSON.stringify(dataSources))
		setDataSources((prev) =>
			prev.map((ds) => (ds.name === sourceName ? { ...ds, enabled } : ds))
		)

		try {
			// In a web environment, enabling a source like Gmail would typically involve
			// a redirect-based OAuth flow. This flow is initiated and handled by the backend.
			// Clicking the switch now directly calls our API endpoint to toggle the source.
			// The backend should handle authentication checks and potential redirects.
			const response = await fetch("/api/settings/data-sources/toggle", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ source: sourceName, enabled })
			})

			const data = await response.json()
			if (!response.ok) {
				// If the server indicates auth is needed (e.g., via a specific error or status code),
				// a real app would redirect the user to the auth URL.
				// For now, we just show the error.
				throw new Error(data.error || "Failed to toggle data source")
			}

			toast.success(`${sourceName} ${enabled ? "enabled" : "disabled"}.`)
			await fetchDataSources() // Refresh data sources from backend
		} catch (error) {
			console.error(`Error updating ${sourceName} data source:`, error)
			toast.error(`Error updating ${sourceName}: ${error.message}`)
			setDataSources(originalDataSources) // Revert UI on any error
		} finally {
			setTogglingSource(null)
		}
	}

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user profile")
			const data = await response.json()
			setUserDetails(data || {})
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
			console.error("Error fetching user details:", error)
		}
	}, [])

	const fetchPricingPlan = useCallback(async () => {
		try {
			const response = await fetch("/api/user/pricing")
			if (!response.ok) throw new Error("Failed to fetch pricing plan")
			const data = await response.json()
			setPricing(data.pricing || "free")
		} catch (error) {
			toast.error(`Error fetching pricing plan: ${error.message}`)
			console.error("Error fetching pricing plan:", error)
		}
	}, [])

	const fetchReferralDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/referral")
			if (!response.ok)
				throw new Error("Failed to fetch referral details")
			const data = await response.json()
			setReferralCode(data.referralCode || "N/A")
			setReferrerStatus(data.referrerStatus || false)
		} catch (error) {
			toast.error(`Error fetching referral details: ${error.message}`)
			console.error("Error fetching referral details:", error)
		}
	}, [])

	const fetchData = useCallback(async () => {
		console.log("Fetching user data...")
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(
					errorData.message || "Failed to fetch user data"
				)
			}
			const result = await response.json()
			if (result.data) {
				console.log("User data fetched successfully.")
			}
		} catch (error) {
			console.error("Error fetching user data:", error)
			toast.error(`Failed to fetch user data: ${error.message}`)
		}
	}, [])

	useEffect(() => {
		console.log("Initial useEffect running...")
		fetchData()
		fetchUserDetails()
		fetchPricingPlan()
		fetchReferralDetails()
		fetchDataSources()
	}, [
		fetchData,
		fetchUserDetails,
		fetchPricingPlan,
		fetchReferralDetails,
		fetchDataSources
	])

	return (
		<div className="h-screen bg-matteblack flex relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-grow flex flex-col h-full bg-matteblack text-white relative overflow-y-auto p-6 md:p-10 custom-scrollbar">
				<div className="flex justify-between items-center mb-8 flex-shrink-0 px-4">
					<h1 className="font-Poppins text-white text-3xl md:text-4xl font-light">
						Settings
					</h1>
					<div className="flex items-center gap-3">
						<button
							onClick={() =>
								window.open(
									"https://existence-sentient.vercel.app/dashboard",
									"_blank"
								)
							}
							className="flex items-center gap-2 py-2 px-4 rounded-full bg-darkblue hover:bg-lightblue text-white text-xs sm:text-sm font-medium transition-colors shadow-md"
							title={
								pricing === "free"
									? "Upgrade for more features"
									: "Manage Subscription"
							}
						>
							<IconRocket size={18} />
							<span>
								{pricing === "free"
									? "Upgrade to Pro"
									: "Manage Pro Plan"}
							</span>
						</button>
						<button
							onClick={() => setShowReferralDialog(true)}
							className="flex items-center gap-2 py-2 px-4 rounded-full bg-neutral-700 hover:bg-neutral-600 text-white text-xs sm:text-sm font-medium transition-colors shadow-md"
							title="Refer a friend"
						>
							<IconGift size={18} />
							<span>Refer Sentient</span>
						</button>
						{/* "Check for Updates" button removed as it's an Electron-specific feature */}
					</div>
				</div>
				<div className="w-full max-w-5xl mx-auto space-y-10 flex-grow">
					<section>
						<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-neutral-700 pb-2">
							Background Data Sources
						</h2>
						<div className="bg-neutral-800/50 p-4 md:p-6 rounded-lg border border-neutral-700">
							<div className="space-y-4">
								{dataSources.length > 0 ? (
									dataSources.map((source) => {
										const SourceIcon =
											source.icon || IconSettingsCog
										return (
											<div
												key={source.name}
												className="flex items-center justify-between py-2"
											>
												<div className="flex items-center gap-3">
													<SourceIcon className="w-6 h-6 text-lightblue" />
													<span className="font-medium text-white text-base">
														{source.display_name ||
															source.name}
													</span>
												</div>
												{togglingSource ===
												source.name ? (
													<IconLoader className="w-5 h-5 animate-spin text-lightblue" />
												) : (
													<Switch
														checked={source.enabled}
														onCheckedChange={(
															enabled
														) =>
															handleToggle(
																source.name,
																enabled
															)
														}
														className={cn(
															"group relative inline-flex h-[24px] w-[44px] flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-lightblue focus:ring-offset-2 focus:ring-offset-neutral-800",
															source.enabled
																? "bg-lightblue"
																: "bg-neutral-600"
														)}
													>
														<span className="sr-only">
															Toggle {source.name}
														</span>
														<span
															aria-hidden="true"
															className={cn(
																"pointer-events-none inline-block h-[20px] w-[20px] transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
																source.enabled
																	? "translate-x-[20px]"
																	: "translate-x-0"
															)}
														/>
													</Switch>
												)}
											</div>
										)
									})
								) : (
									<p className="text-gray-400 italic text-center py-4">
										Data source settings loading or none
										available...
									</p>
								)}
							</div>
						</div>
					</section>

					{showReferralDialog && (
						<ModalDialog
							title="Referral Code"
							description={`Share this code with friends: ${referralCode === "N/A" || !referralCode ? "Loading..." : referralCode}`}
							extraContent={
								referrerStatus ? (
									<p className="text-sm text-green-400">
										Referrer status: Active
									</p>
								) : (
									<p className="text-sm text-yellow-400">
										Referrer status: Inactive
									</p>
								)
							}
							onConfirm={() => setShowReferralDialog(false)}
							confirmButtonText="Close"
							cancelButton={false}
						/>
					)}
				</div>
			</div>
		</div>
	)
}

export default Settings
