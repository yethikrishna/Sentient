"use client"

import toast from "react-hot-toast"
import ModalDialog from "@components/ModalDialog"
import {
	IconMail,
	IconCalendarEvent,
	IconWorldSearch,
	IconLoader,
	IconSettingsCog,
	IconBrandGoogleDrive,
	IconBrandSlack,
	IconBrandNotion,
	IconPlugConnected,
	IconPlugOff,
	IconPlus,
	IconCloud,
	IconChartPie,
	IconBrain,
	IconBrandGithub,
	IconNews,
	IconBrandGoogle,
	IconUser,
	IconFileText,
	IconLock,
	IconLockOpen,
	IconPresentation,
	IconTable,
	IconMapPin,
	IconShoppingCart,
	IconLink,
	IconMenu2,
	IconChevronDown,
	IconFilterOff,
	IconX
} from "@tabler/icons-react"
import { useState, useEffect, useCallback, useRef } from "react"
import Sidebar from "@components/Sidebar"
import React from "react"
import { useSmoothScroll } from "@hooks/useSmoothScroll"
import { cn } from "@utils/cn"

const integrationIcons = {
	gmail: IconMail,
	gcalendar: IconCalendarEvent,
	internet_search: IconWorldSearch,
	gdrive: IconBrandGoogleDrive,
	gdocs: IconFileText,
	gslides: IconPresentation,
	gsheets: IconTable,
	gmaps: IconMapPin,
	gshopping: IconShoppingCart,
	slack: IconBrandSlack,
	notion: IconBrandNotion,
	accuweather: IconCloud,
	quickchart: IconChartPie,
	memory: IconBrain,
	google_search: IconWorldSearch,
	github: IconBrandGithub,
	news: IconNews
}

// Hardcoded configuration for manual integrations
const MANUAL_INTEGRATION_CONFIGS = {
	slack: {
		instructions: [
			"1. Go to api.slack.com/apps and create a new app from scratch.",
			"2. In 'OAuth & Permissions', add User Token Scopes like `chat:write`, `channels:read`.",
			"3. Install the app and copy the 'User OAuth Token' (starts with `xoxp-`).",
			"4. Find your 'Team ID' (starts with `T`) from your Slack URL or settings."
		],
		fields: [
			{ id: "token", label: "User OAuth Token", type: "password" },
			{ id: "team_id", label: "Team ID", type: "text" }
		]
	},
	notion: {
		instructions: [
			"Go to notion.so/my-integrations to create a new integration.",
			"Give it a name and associate it with a workspace.",
			"On the next screen, copy the 'Internal Integration Token'.",
			"Go to the Notion pages or databases you want Sentient to access.",
			"Click the '...' menu, find 'Add connections', and select your new integration."
		],
		fields: [
			{
				id: "token",
				label: "Internal Integration Token",
				type: "password"
			}
		]
	}
}

const ManualTokenEntryModal = ({ integration, onClose, onSuccess }) => {
	const [credentials, setCredentials] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)

	if (!integration) {
		return null
	}

	const config = MANUAL_INTEGRATION_CONFIGS[integration?.name]
	const instructions = config?.instructions || []
	const fields = config?.fields || []

	if (fields.length === 0) {
		console.error(
			`No fields configured for manual integration: ${integration?.name}`
		)
		return null
	}

	const handleChange = (e) => {
		setCredentials({
			...credentials,
			[e.target.name]: e.target.value
		})
	}

	const handleSubmit = async () => {
		for (const field of fields) {
			if (!credentials[field.id]?.trim()) {
				toast.error(`Please provide the ${field.label}.`)
				return
			}
		}

		setIsSubmitting(true)
		try {
			const response = await fetch(
				"/api/settings/integrations/connect/manual",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						service_name: integration.name,
						credentials
					})
				}
			)

			const data = await response.json()
			if (!response.ok) {
				throw new Error(
					data.error ||
						`Failed to connect ${integration.display_name}`
				)
			}

			toast.success(`${integration.display_name} connected successfully!`)
			onSuccess()
			onClose()
		} catch (error) {
			console.error(
				`Error connecting ${integration.display_name}:`,
				error
			)
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const modalContent = (
		<div className="text-left space-y-4 my-4">
			<div>
				<h4 className="font-semibold text-gray-300 mb-2">
					Instructions:
				</h4>
				<ol className="list-decimal list-inside space-y-1 text-sm text-gray-400">
					{instructions.map((step, index) => (
						<li key={index}>{step}</li>
					))}
				</ol>
			</div>
			<div className="space-y-3">
				{fields.map((field) => (
					<div key={field.id}>
						<label
							htmlFor={field.id}
							className="block text-sm font-medium text-gray-300 mb-1"
						>
							Enter {field.label}
						</label>
						<input
							type={field.type}
							name={field.id}
							id={field.id}
							onChange={handleChange}
							value={credentials[field.id] || ""}
							className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
							autoComplete="off"
						/>
					</div>
				))}
			</div>
		</div>
	)

	return (
		<ModalDialog
			title={`Connect to ${integration.display_name}`}
			description="Follow the instructions below and enter your credentials."
			onConfirm={handleSubmit}
			onCancel={onClose}
			confirmButtonText={isSubmitting ? "Connecting..." : "Connect"}
			isConfirmDisabled={isSubmitting}
			extraContent={modalContent}
		/>
	)
}

const PrivacySettings = () => {
	const [filters, setFilters] = useState([])
	const [newFilter, setNewFilter] = useState("")
	const [isLoading, setIsLoading] = useState(true)

	const fetchFilters = useCallback(async () => {
		setIsLoading(true)
		try {
			const response = await fetch("/api/settings/privacy-filters")
			if (!response.ok) throw new Error("Failed to fetch filters.")
			const data = await response.json()
			setFilters(data.filters || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchFilters()
	}, [fetchFilters])

	const handleAddFilter = async () => {
		if (!newFilter.trim()) {
			toast.error("Filter cannot be empty.")
			return
		}
		const updatedFilters = [...filters, newFilter.trim()]
		await handleSaveFilters(updatedFilters)
		setNewFilter("") // Clear input after adding
	}

	const handleDeleteFilter = async (filterToDelete) => {
		const updatedFilters = filters.filter((f) => f !== filterToDelete)
		await handleSaveFilters(updatedFilters)
	}

	const handleSaveFilters = async (updatedFilters) => {
		setIsLoading(true)
		try {
			const response = await fetch("/api/settings/privacy-filters", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ filters: updatedFilters })
			})
			if (!response.ok) throw new Error("Failed to save filters.")
			toast.success("Privacy filters updated.")
			setFilters(updatedFilters)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}

	return (
		<section>
			<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2">
				Privacy Filters
			</h2>
			<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)]">
				<p className="text-gray-400 text-sm mb-4">
					Add keywords to prevent emails or events containing them
					from being processed by the proactive pipeline.
				</p>
				<div className="flex gap-2 mb-4">
					<input
						type="text"
						value={newFilter}
						onChange={(e) => setNewFilter(e.target.value)}
						onKeyDown={(e) =>
							e.key === "Enter" && handleAddFilter()
						}
						placeholder="Add a new filter keyword..."
						className="flex-grow bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
					/>
					<button
						onClick={handleAddFilter}
						disabled={isLoading}
						className="flex flex-row items-center py-2 px-4 rounded-md bg-darkblue hover:bg-lightblue text-white font-medium transition-colors"
					>
						<IconPlus className="w-4 h-4 mr-2" /> Add
					</button>
				</div>
				<div className="flex flex-wrap gap-2">
					{filters.map((filter, index) => (
						<div
							key={index}
							className="flex items-center gap-2 bg-[var(--color-primary-surface-elevated)] rounded-full py-1.5 px-3 text-sm text-gray-200"
						>
							<span>{filter}</span>
							<button onClick={() => handleDeleteFilter(filter)}>
								<IconX
									size={14}
									className="text-gray-500 hover:text-red-400"
								/>
							</button>
						</div>
					))}
				</div>
				{isLoading && (
					<div className="flex justify-center mt-4">
						<IconLoader className="w-6 h-6 animate-spin text-[var(--color-accent-blue)]" />
					</div>
				)}
			</div>
		</section>
	)
}

const Settings = () => {
	const [userDetails, setUserDetails] = useState({})
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [userIntegrations, setUserIntegrations] = useState([])
	const [defaultTools, setDefaultTools] = useState([])
	const [loadingIntegrations, setLoadingIntegrations] = useState(true)
	const [activeManualIntegration, setActiveManualIntegration] = useState(null)
	const [processingIntegration, setProcessingIntegration] = useState(null)
	const scrollRef = useRef(null)

	useSmoothScroll(scrollRef)

	// --- CORRECTED: Specific list of Google services ---
	const googleServices = [
		"gmail",
		"gcalendar",
		"gdrive",
		"gdocs",
		"gslides",
		"gsheets"
	]

	const fetchIntegrations = useCallback(async () => {
		setLoadingIntegrations(true)
		try {
			const response = await fetch("/api/settings/integrations")
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to fetch integrations")
			}
			const integrationsWithIcons = (
				Array.isArray(data.integrations) ? data.integrations : []
			).map((ds) => ({
				...ds,
				icon: integrationIcons[ds.name] || IconSettingsCog
			}))

			const hiddenTools = [
				"google_search",
				"progress_updater",
				"chat_tools",
				"journal"
			]

			const userConnectable = integrationsWithIcons.filter(
				(i) =>
					(i.auth_type === "oauth" || i.auth_type === "manual") &&
					!hiddenTools.includes(i.name)
			)
			const builtIn = integrationsWithIcons.filter(
				(i) =>
					i.auth_type === "builtin" && !hiddenTools.includes(i.name)
			)
			setUserIntegrations(userConnectable)
			setDefaultTools(builtIn)
		} catch (error) {
			console.error("Error fetching integrations:", error)
			toast.error(`Error fetching integrations: ${error.message}`)
		} finally {
			setLoadingIntegrations(false)
		}
	}, [])

	const handleConnect = (integration) => {
		if (integration.auth_type === "oauth") {
			const { name: serviceName, client_id: clientId } = integration
			if (!clientId) {
				toast.error(
					`Client ID for ${integration.display_name} is not configured.`
				)
				return
			}

			const redirectUri = `${window.location.origin}/api/settings/integrations/connect/oauth/callback`
			const state = serviceName
			let authUrl = ""

			const scopes = {
				gdrive: "https://www.googleapis.com/auth/drive",
				gcalendar: "https://www.googleapis.com/auth/calendar",
				gmail: "https://mail.google.com/",
				gdocs: "https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive",
				gslides:
					"https://www.googleapis.com/auth/presentations https://www.googleapis.com/auth/drive",
				gsheets: "https://www.googleapis.com/auth/spreadsheets",
				gmaps: "https://www.googleapis.com/auth/cloud-platform",
				gshopping: "https://www.googleapis.com/auth/content",
				github: "repo user"
			}

			const scope =
				scopes[serviceName] ||
				"https://www.googleapis.com/auth/userinfo.email"

			// --- CORRECTED: Use precise list for Google services ---
			if (googleServices.includes(serviceName)) {
				authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent&state=${state}`
			} else if (serviceName === "github") {
				authUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scope)}&state=${state}`
			}

			if (authUrl) {
				window.location.href = authUrl
			} else {
				toast.error(
					`OAuth flow for ${integration.display_name} is not implemented.`
				)
			}
		} else if (integration.auth_type === "manual") {
			if (MANUAL_INTEGRATION_CONFIGS[integration.name]) {
				setActiveManualIntegration(integration)
			} else {
				toast.error(
					`UI configuration for ${integration.display_name} not found.`
				)
			}
		}
	}

	const handleDisconnect = async (integrationName) => {
		const displayName =
			userIntegrations.find((i) => i.name === integrationName)
				?.display_name || integrationName

		if (
			!window.confirm(
				`Are you sure you want to disconnect ${displayName}?`
			)
		) {
			return
		}

		setProcessingIntegration(integrationName)
		try {
			const response = await fetch(
				"/api/settings/integrations/disconnect",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ service_name: integrationName })
				}
			)
			const data = await response.json()
			if (!response.ok) {
				throw new Error(
					data.error || `Failed to disconnect ${displayName}`
				)
			}
			toast.success(`${displayName} disconnected.`)
			fetchIntegrations()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setProcessingIntegration(null)
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
			toast.error(`Failed to fetch user data: ${error.message}`)
		}
	}, [])

	useEffect(() => {
		fetchData()
		fetchUserDetails()
		fetchIntegrations()

		const urlParams = new URLSearchParams(window.location.search)
		const success = urlParams.get("integration_success")
		const error = urlParams.get("integration_error")

		if (success) {
			toast.success(`Successfully connected to ${success}!`)
			window.history.replaceState({}, document.title, "/settings")
		} else if (error) {
			toast.error(`Connection failed: ${error}`)
			window.history.replaceState({}, document.title, "/settings")
		}
	}, [fetchData, fetchUserDetails, fetchIntegrations])

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)]">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex flex-col sm:flex-row items-center justify-between p-4 bg-[var(--color-primary-background)] border-b border-[var(--color-primary-surface)] gap-4">
					<div className="flex items-center gap-4 w-full sm:w-auto">
						<button
							onClick={() => setSidebarVisible(true)}
							className="text-[var(--color-text-primary)] md:hidden"
						>
							<IconMenu2 />
						</button>
						<h1 className="font-Poppins text-[var(--color-text-primary)] text-2xl sm:text-3xl font-light">
							Settings
						</h1>
					</div>
					<div></div>
				</header>
				<main
					ref={scrollRef}
					className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 no-scrollbar"
				>
					<div className="w-full max-w-5xl mx-auto space-y-10">
						<PrivacySettings />
						<section>
							<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2">
								Connected Apps & Integrations
							</h2>
							<div className="bg-[var(--color-primary-surface)]/50 p-2 md:p-4 rounded-lg border border-[var(--color-primary-surface-elevated)]">
								<div className="divide-y divide-[var(--color-primary-surface-elevated)]/50">
									{loadingIntegrations ? (
										<div className="flex justify-center items-center py-10">
											<IconLoader className="w-8 h-8 animate-spin text-[var(--color-accent-blue)]" />
										</div>
									) : userIntegrations.length > 0 ? (
										userIntegrations.map((integration) => {
											const IntegrationIcon =
												integration.icon ||
												IconSettingsCog
											const isProcessing =
												processingIntegration ===
												integration.name

											return (
												<div
													key={integration.name}
													className="flex items-center justify-between p-4"
												>
													<div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
														<IntegrationIcon className="w-8 h-8 text-[var(--color-accent-blue)]" />
														<div className="flex-1 min-w-0">
															<h3 className="font-semibold text-[var(--color-text-primary)] text-base sm:text-lg truncate">
																{
																	integration.display_name
																}
															</h3>
															<details className="mt-1 text-gray-400 text-xs sm:text-sm group">
																<summary className="list-none flex items-center cursor-pointer hover:text-white transition-colors w-fit">
																	<span>
																		Details
																	</span>
																	<IconChevronDown
																		size={
																			14
																		}
																		className="ml-1 transition-transform duration-200 group-open:rotate-180"
																	/>
																</summary>
																<p className="mt-2 pt-2 border-t border-neutral-700/50">
																	{
																		integration.description
																	}
																</p>
															</details>
														</div>
													</div>
													<div className="w-32 sm:w-40 text-right flex-shrink-0">
														{isProcessing ? (
															<IconLoader className="w-6 h-6 animate-spin text-[var(--color-accent-blue)] ml-auto" />
														) : integration.connected ? (
															<button
																onClick={() =>
																	handleDisconnect(
																		integration.name
																	)
																}
																className="flex items-center justify-center gap-1 sm:gap-2 w-full py-2 px-3 rounded-md bg-[var(--color-accent-red)]/20 hover:bg-[var(--color-accent-red)]/40 text-red-400 text-sm font-medium transition-colors"
															>
																<IconPlugOff
																	size={16}
																/>
																<span>
																	Disconnect
																</span>
															</button>
														) : (
															<button
																onClick={() =>
																	handleConnect(
																		integration
																	)
																}
																className="flex items-center justify-center gap-1 sm:gap-2 w-full py-2 px-3 rounded-md bg-[var(--color-accent-blue)]/50 hover:bg-[var(--color-accent-blue)]/70 text-white text-sm font-medium transition-colors"
															>
																<IconPlugConnected
																	size={16}
																/>
																<span>
																	Connect
																</span>
															</button>
														)}
													</div>
												</div>
											)
										})
									) : (
										<p className="text-gray-400 italic text-center py-8">
											No integrations available.
										</p>
									)}
								</div>
							</div>
						</section>

						<section>
							<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2">
								Default System Tools
							</h2>
							<div className="bg-[var(--color-primary-surface)]/50 p-2 md:p-4 rounded-lg border border-[var(--color-primary-surface-elevated)]">
								<div className="divide-y divide-[var(--color-primary-surface-elevated)]/50">
									{loadingIntegrations ? (
										<div className="flex justify-center items-center py-10">
											<IconLoader className="w-8 h-8 animate-spin text-[var(--color-accent-blue)]" />
										</div>
									) : defaultTools.length > 0 ? (
										defaultTools.map((tool) => {
											const ToolIcon =
												tool.icon || IconSettingsCog
											return (
												<div
													key={tool.name}
													className="flex items-center justify-between p-4"
												>
													<div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
														<ToolIcon className="w-8 h-8 text-[var(--color-text-muted)]" />
														<div className="flex-1 min-w-0">
															<h3 className="font-semibold text-[var(--color-text-primary)] text-base sm:text-lg truncate">
																{
																	tool.display_name
																}
															</h3>
															<details className="mt-1 text-gray-400 text-xs sm:text-sm group">
																<summary className="list-none flex items-center cursor-pointer hover:text-white transition-colors w-fit">
																	<span>
																		Details
																	</span>
																	<IconChevronDown
																		size={
																			14
																		}
																		className="ml-1 transition-transform duration-200 group-open:rotate-180"
																	/>
																</summary>
																<p className="mt-2 pt-2 border-t border-neutral-700/50">
																	{
																		tool.description
																	}
																</p>
															</details>
														</div>
													</div>
												</div>
											)
										})
									) : (
										<p className="text-gray-400 italic text-center py-8">
											No default tools available.
										</p>
									)}
								</div>
							</div>
						</section>
					</div>

					{activeManualIntegration && (
						<ManualTokenEntryModal
							integration={activeManualIntegration}
							onClose={() => setActiveManualIntegration(null)}
							onSuccess={() => fetchIntegrations()}
						/>
					)}
				</main>
			</div>
		</div>
	)
}

export default Settings
