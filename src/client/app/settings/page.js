"use client"

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
	IconBrandGoogleDrive,
	IconBrandSlack,
	IconBrandNotion,
	IconPlugConnected,
	IconPlugOff,
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
	IconLink
} from "@tabler/icons-react"
import { useState, useEffect, useCallback } from "react"
import Sidebar from "@components/Sidebar"
import React from "react"
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
							{field.label}
						</label>
						<input
							type={field.type}
							name={field.id}
							id={field.id}
							onChange={handleChange}
							value={credentials[field.id] || ""}
							className="w-full bg-neutral-700 border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lightblue"
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

const GoogleAuthSettings = ({ mode, onModeChange, onSaveSuccess }) => {
	const [credentials, setCredentials] = useState("")
	const [isSaving, setIsSaving] = useState(false)

	const handleSave = async () => {
		if (mode === "custom") {
			try {
				JSON.parse(credentials)
			} catch (e) {
				toast.error(
					"Invalid JSON. Please paste the entire content of your Service Account key file."
				)
				return
			}
		}

		setIsSaving(true)
		try {
			const res = await fetch("/api/settings/google-auth", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					mode: mode,
					credentialsJson: mode === "custom" ? credentials : undefined
				})
			})

			const data = await res.json()
			if (!res.ok) {
				throw new Error(
					data.detail || "Failed to save Google settings."
				)
			}
			toast.success(
				data.message || "Google API settings saved successfully!"
			)
			setCredentials("") // Clear credentials after successful save
			onSaveSuccess(mode) // Notify parent of the successful change
		} catch (error) {
			toast.error(`Error: ${error.message}`)
		} finally {
			setIsSaving(false)
		}
	}

	const renderInstructions = () => (
		<div className="mt-4 text-sm text-gray-400 space-y-3 p-4 bg-neutral-900/50 rounded-lg border border-neutral-700">
			<h4 className="font-semibold text-gray-200">
				How to get your Service Account Key:
			</h4>
			<ol className="list-decimal list-inside space-y-2">
				<li>
					Go to the{" "}
					<a
						href="https://console.cloud.google.com/"
						target="_blank"
						rel="noopener noreferrer"
						className="text-lightblue hover:underline"
					>
						Google Cloud Console
					</a>{" "}
					and create a new project.
				</li>
				<li>
					Enable the APIs you want to use (e.g., Gmail API, Google
					Drive API, Google Calendar API, Google Maps Platform APIs,
					Google Shopping Content API) in the "APIs & Services"
					dashboard.
				</li>
				<li>
					Go to "Credentials", click "Create Credentials", and select
					"Service account".
				</li>
				<li>
					Give the service account a name, grant it appropriate roles
					(e.g., "Project Viewer"), and click "Done".
				</li>
				<li>
					Find your new service account, go to the "Keys" tab, click
					"Add Key", choose "Create new key", select "JSON", and
					download the file.
				</li>
				<li>
					Open the downloaded JSON file and paste its entire content
					into the text box above.
				</li>
				<li className="font-bold text-yellow-400">
					Important: You must enable{" "}
					<a
						href="https://developers.google.com/workspace/guides/configure-domain-wide-delegation"
						target="_blank"
						rel="noopener noreferrer"
						className="text-lightblue hover:underline"
					>
						Domain-Wide Delegation
					</a>{" "}
					for your service account in your Google Workspace Admin
					Console. You must grant it the following scopes:
					<ul className="list-disc list-inside mt-1 pl-4 font-mono text-xs text-gray-300">
						<li>https://www.googleapis.com/auth/calendar</li>
						<li>https://www.googleapis.com/auth/drive</li>
						<li>https://mail.google.com/</li>
						<li>https://www.googleapis.com/auth/documents</li>
						<li>https://www.googleapis.com/auth/presentations</li>
						<li>https://www.googleapis.com/auth/spreadsheets</li>
						<li>https://www.googleapis.com/auth/cloud-platform</li>
						<li>https://www.googleapis.com/auth/content</li>
					</ul>
				</li>
			</ol>
		</div>
	)

	return (
		<div className="bg-neutral-800/50 p-4 md:p-6 rounded-lg border border-neutral-700">
			<div className="flex items-center gap-4">
				<IconBrandGoogle className="w-8 h-8 text-white" />
				<div>
					<h3 className="font-semibold text-white text-lg">
						Google Project Configuration
					</h3>
					<p className="text-gray-400 text-sm">
						Choose how to authenticate with Google services.
					</p>
				</div>
			</div>

			<div className="mt-6 flex items-center space-x-4">
				<button
					onClick={() => onModeChange("default")}
					className={cn(
						"flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2",
						mode === "default"
							? "bg-lightblue text-white"
							: "bg-neutral-700 hover:bg-neutral-600"
					)}
				>
					<IconRocket size={16} />
					Use Our Default Project
				</button>
				<button
					onClick={() => onModeChange("custom")}
					className={cn(
						"flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2",
						mode === "custom"
							? "bg-green-600 text-white"
							: "bg-neutral-700 hover:bg-neutral-600"
					)}
				>
					<IconUser size={16} />
					Use My Own Project
				</button>
			</div>

			{mode === "custom" && (
				<div className="mt-6">
					<label
						htmlFor="gcp-credentials"
						className="block text-sm font-medium text-gray-300 mb-2"
					>
						Service Account JSON Key
					</label>
					<textarea
						id="gcp-credentials"
						rows={8}
						className="w-full bg-neutral-900 border border-neutral-600 rounded-md p-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-xs"
						placeholder="Paste the content of your service account JSON file here..."
						value={credentials}
						onChange={(e) => setCredentials(e.target.value)}
					/>
					{renderInstructions()}
				</div>
			)}

			<div className="mt-6 flex justify-end">
				<button
					onClick={handleSave}
					disabled={isSaving}
					className="flex items-center justify-center gap-2 py-2 px-5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors disabled:opacity-50"
				>
					{isSaving ? (
						<IconLoader className="animate-spin" size={18} />
					) : (
						<IconFileText size={18} />
					)}
					<span>{isSaving ? "Saving..." : "Save Settings"}</span>
				</button>
			</div>
		</div>
	)
}

const Settings = () => {
	const [userDetails, setUserDetails] = useState({})
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [pricing, setPricing] = useState("free")
	const [showReferralDialog, setShowReferralDialog] = useState(false)
	const [referralCode, setReferralCode] = useState("DUMMY")
	const [referrerStatus, setReferrerStatus] = useState(false)
	const [userIntegrations, setUserIntegrations] = useState([])
	const [defaultTools, setDefaultTools] = useState([])
	const [loadingIntegrations, setLoadingIntegrations] = useState(true)
	const [activeManualIntegration, setActiveManualIntegration] = useState(null)
	const [processingIntegration, setProcessingIntegration] = useState(null)
	const [googleAuthMode, setGoogleAuthMode] = useState("default")
	const [loadingGoogleAuthMode, setLoadingGoogleAuthMode] = useState(true)

	const fetchGoogleAuthMode = useCallback(async () => {
		setLoadingGoogleAuthMode(true)
		try {
			const res = await fetch("/api/settings/google-auth")
			if (!res.ok)
				throw new Error("Failed to fetch Google auth settings.")
			const data = await res.json()
			setGoogleAuthMode(data.mode || "default")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setLoadingGoogleAuthMode(false)
		}
	}, [])

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
				"internet_search",
				"google_search",
				"gmaps",
				"gshopping"
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

			// Define scopes required by our default OAuth app
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

			if (serviceName.startsWith("g")) {
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

	const fetchPricingPlan = useCallback(async () => {
		try {
			const response = await fetch("/api/user/pricing")
			if (!response.ok) throw new Error("Failed to fetch pricing plan")
			const data = await response.json()
			setPricing(data.pricing || "free")
		} catch (error) {
			toast.error(`Error fetching pricing plan: ${error.message}`)
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
		fetchPricingPlan()
		fetchReferralDetails()
		fetchIntegrations()
		fetchGoogleAuthMode()

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
	}, [
		fetchData,
		fetchUserDetails,
		fetchPricingPlan,
		fetchReferralDetails,
		fetchIntegrations,
		fetchGoogleAuthMode
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
					</div>
				</div>
				<div className="w-full max-w-5xl mx-auto space-y-10 flex-grow">
					<section>
						<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-neutral-700 pb-2">
							API & Service Configuration
						</h2>
						{loadingGoogleAuthMode ? (
							<div className="flex justify-center items-center py-10">
								<IconLoader className="w-8 h-8 animate-spin text-lightblue" />
							</div>
						) : (
							<GoogleAuthSettings
								mode={googleAuthMode}
								onModeChange={setGoogleAuthMode}
								onSaveSuccess={() => {
									fetchGoogleAuthMode()
									fetchIntegrations()
								}}
							/>
						)}
					</section>

					<section>
						<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-neutral-700 pb-2">
							Connected Apps & Integrations
						</h2>
						<div className="bg-neutral-800/50 p-2 md:p-4 rounded-lg border border-neutral-700">
							<div className="divide-y divide-neutral-700/50">
								{loadingIntegrations ? (
									<div className="flex justify-center items-center py-10">
										<IconLoader className="w-8 h-8 animate-spin text-lightblue" />
									</div>
								) : userIntegrations.length > 0 ? (
									userIntegrations.map((integration) => {
										const IntegrationIcon =
											integration.icon || IconSettingsCog
										const isProcessing =
											processingIntegration ===
											integration.name
										const isGoogleServiceInCustomMode =
											integration.name.startsWith("g") &&
											googleAuthMode === "custom"

										return (
											<div
												key={integration.name}
												className="flex items-center justify-between p-4"
											>
												<div className="flex items-center gap-4">
													<IntegrationIcon className="w-8 h-8 text-lightblue" />
													<div>
														<h3 className="font-semibold text-white text-lg">
															{
																integration.display_name
															}
														</h3>
														<p className="text-gray-400 text-sm">
															{
																integration.description
															}
														</p>
													</div>
												</div>
												<div className="w-40 text-right">
													{isGoogleServiceInCustomMode ? (
														<div className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-md bg-green-600/20 text-green-400 text-xs font-medium cursor-default">
															<IconLockOpen
																size={14}
															/>
															<span>
																Managed by
																Custom Project
															</span>
														</div>
													) : isProcessing ? (
														<IconLoader className="w-6 h-6 animate-spin text-lightblue ml-auto" />
													) : integration.connected ? (
														<button
															onClick={() =>
																handleDisconnect(
																	integration.name
																)
															}
															className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-md bg-red-600/20 hover:bg-red-600/40 text-red-400 text-sm font-medium transition-colors"
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
															className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-md bg-blue-600/50 hover:bg-blue-600/70 text-white text-sm font-medium transition-colors"
														>
															<IconPlugConnected
																size={16}
															/>
															<span>Connect</span>
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
						<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-neutral-700 pb-2">
							Default System Tools
						</h2>
						<div className="bg-neutral-800/50 p-2 md:p-4 rounded-lg border border-neutral-700">
							<div className="divide-y divide-neutral-700/50">
								{loadingIntegrations ? (
									<div className="flex justify-center items-center py-10">
										<IconLoader className="w-8 h-8 animate-spin text-lightblue" />
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
												<div className="flex items-center gap-4">
													<ToolIcon className="w-8 h-8 text-gray-400" />
													<div>
														<h3 className="font-semibold text-white text-lg">
															{tool.display_name}
														</h3>
														<p className="text-gray-400 text-sm">
															{tool.description}
														</p>
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

					{activeManualIntegration && (
						<ManualTokenEntryModal
							integration={activeManualIntegration}
							onClose={() => setActiveManualIntegration(null)}
							onSuccess={() => fetchIntegrations()}
						/>
					)}

					{showReferralDialog && (
						<ModalDialog
							title="Referral Code"
							description={`Share this code with friends: ${
								referralCode === "N/A" || !referralCode
									? "Loading..."
									: referralCode
							}`}
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
