// src/client/app/settings/page.js
"use client"

import { useState, useEffect, useCallback } from "react" 
import Sidebar from "@components/Sidebar"
import ProIcon from "@components/ProIcon"
import toast from "react-hot-toast"
import ModalDialog from "@components/ModalDialog"
import {
	IconGift,
	IconRocket,
	IconMail,
	IconCalendarEvent,
	IconWorldSearch, 
	IconLoader,
	IconSettingsCog, 
	IconDownload 
} from "@tabler/icons-react"
import React from "react"
import { Switch } from "@radix-ui/react-switch" 
import { cn } from "@utils/cn" 

const dataSourceIcons = {
	gmail: IconMail,
	gcalendar: IconCalendarEvent, // Example, not yet implemented for polling
	internet_search: IconWorldSearch // Example, not yet implemented for polling
}

const Settings = () => {
	const [userDetails, setUserDetails] = useState({})
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [pricing, setPricing] = useState("free")
	const [showReferralDialog, setShowReferralDialog] = useState(false)
	const [referralCode, setReferralCode] = useState("DUMMY")
	const [referrerStatus, setReferrerStatus] = useState(false)
	const [dataSources, setDataSources] = useState([]) 
	// Removed graph-related states as they are on memory page now
	const [updateCheckLoading, setUpdateCheckLoading] = useState(false)
	const [togglingSource, setTogglingSource] = useState(null) 


	const fetchDataSources = useCallback(async () => {
		console.log("Fetching data sources...")
		try {
			const response = await window.electron.invoke("get-data-sources")
			if (response.error) {
				console.error("Error fetching data sources:", response.error)
				toast.error(`Error fetching data sources: ${response.error}`) 
				setDataSources([])
			} else {
				const sourcesWithIcons = (
					Array.isArray(response.data_sources)
						? response.data_sources
						: []
				).map((ds) => ({
					...ds,
					icon: dataSourceIcons[ds.name] || IconSettingsCog 
				})) 
				setDataSources(sourcesWithIcons)
				console.log("Data sources fetched:", sourcesWithIcons)
			}
		} catch (error) {
			console.error("Error fetching data sources:", error)
			toast.error(`Error fetching data sources: ${error.message || error}`)
			setDataSources([])
		}
	}, []) 

	const handleToggle = async (sourceName, enabled) => {
		console.log(`Toggling ${sourceName} to ${enabled}`)
		setTogglingSource(sourceName)

		const originalDataSources = JSON.parse(JSON.stringify(dataSources)); // Deep copy for reliable revert
		setDataSources((prev) =>
			prev.map((ds) => (ds.name === sourceName ? { ...ds, enabled } : ds))
		)

		try {
			if (sourceName === "gmail" && enabled) {
				console.log("Initiating Google OAuth for Gmail...")
				// The 'start-google-auth' IPC will handle storing token on server
				const authResult = await window.electron.startGoogleAuth("gmail") 

				if (authResult && authResult.success) {
					toast.success("Gmail connected successfully!")
					// After successful OAuth & server-side token storage, now enable the source on the server
					const response = await window.electron.invoke(
						"set-data-source-enabled",
						{ source: sourceName, enabled: true } // Explicitly set enabled to true
					)
					if (response.error) throw new Error(response.error)
					toast.success(`${sourceName} enabled. Data polling will begin shortly.`)
                    await fetchDataSources(); // Refresh data sources to reflect the change from backend
				} else {
					toast.error(authResult?.message || "Gmail connection failed or was cancelled.")
					setDataSources(originalDataSources) // Revert UI
				}
			} else {
				// For other sources or disabling Gmail
				const response = await window.electron.invoke(
					"set-data-source-enabled",
					{ source: sourceName, enabled }
				)
				if (response.error) throw new Error(response.error)
				toast.success(`${sourceName} ${enabled ? "enabled" : "disabled"}.`)
                await fetchDataSources(); // Refresh data sources
			}
		} catch (error) {
			console.error(`Error updating ${sourceName} data source:`, error)
			toast.error(`Error updating ${sourceName}: ${error.message || "Unknown error"}`)
			setDataSources(originalDataSources) // Revert UI on any error
		} finally {
			setTogglingSource(null) 
		}
	}


	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await window.electron?.invoke("get-profile")
			setUserDetails(response || {}) 
		} catch (error) {
			toast.error("Error fetching user details for sidebar.")
			console.error("Error fetching user details:", error)
		}
	}, []) 

	const fetchPricingPlan = useCallback(async () => {
		try {
			const response = await window.electron?.invoke("fetch-pricing-plan")
			setPricing(response || "free") 
		} catch (error) {
			toast.error("Error fetching pricing plan.")
			console.error("Error fetching pricing plan:", error)
		}
	}, []) 

	const fetchReferralDetails = useCallback(async () => {
		try {
			const code = await window.electron?.invoke("fetch-referral-code")
			const status = await window.electron?.invoke(
				"fetch-referrer-status"
			)
			setReferralCode(code || "N/A") 
			setReferrerStatus(status || false) 
		} catch (error) {
			toast.error("Error fetching referral details.")
			console.error("Error fetching referral details:", error)
		}
	}, []) 

	const handleCheckForUpdates = useCallback(async () => {
		setUpdateCheckLoading(true)
		console.log("Initiating manual update check via IPC...")
		try {
			const response = await window.electron.invoke(
				"check-for-updates-manual"
			)
			if (response.success) {
				toast.success(response.message)
				console.log("Manual update check initiated:", response.message)
			} else {
				toast.error(response.message)
				console.error("Manual update check failed:", response.message)
			}
		} catch (error) {
			toast.error("Error initiating update check.")
			console.error("Error calling check-for-updates-manual IPC:", error)
		} finally {
			setUpdateCheckLoading(false)
		}
	}, []) 

	// Fetching generic user data (which might include social connection status or other settings)
    // This is distinct from just the profile used for the sidebar.
	const fetchData = useCallback(async () => {
		console.log("Fetching user data (excluding social media connection status for this specific function)...")
		try {
			const response = await window.electron?.invoke("get-user-data")
			if (response.status === 200 && response.data) {
				console.log("User data fetched successfully (ignoring specific social media flags here).")
				// Example: if response.data contains { "data_sources": {"gmail_connected": true} }
                // You could use this to initialize switch states if needed, though `fetchDataSources` is primary for that.
			} else {
				console.error("Error fetching DB data, status:", response?.status, "response:", response )
				toast.error(`Failed to fetch user data: ${response?.message || response?.error || "Unknown error"}`)
			}
		} catch (error) {
			console.error("Error fetching user data:", error)
            toast.error(`Failed to fetch user data: ${error.message || error}`);
		}
	}, []) 

	useEffect(() => {
		console.log("Initial useEffect running...")
		fetchData()
		fetchUserDetails()
		fetchPricingPlan()
		fetchReferralDetails()
		fetchDataSources()
	}, [ // Dependencies for initial data load
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
									"https://existence-sentient.vercel.app/dashboard", // Example dashboard URL
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
						<button
							onClick={handleCheckForUpdates}
							disabled={updateCheckLoading}
							className="flex items-center gap-2 py-2 px-4 rounded-full bg-purple-700 hover:bg-purple-600 text-white text-xs sm:text-sm font-medium transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
							title="Check for application updates"
						>
							{updateCheckLoading ? (
								<IconLoader
									size={18}
									className="animate-spin"
								/>
							) : (
								<IconDownload size={18} />
							)}
							<span>
								{updateCheckLoading
									? "Checking..."
									: "Check for Updates"}
							</span>
						</button>
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
														{source.display_name || source.name} {/* Use display_name */}
													</span>
												</div>
												{togglingSource === source.name ? (
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
										Data source settings loading or none available...
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
							cancelButton={false} // No cancel button needed for info dialog
						/>
					)}
				</div>
			</div>
		</div>
	)
}

export default Settings