"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import toast from "react-hot-toast"
import {
	IconLoader,
	IconSettingsCog,
	IconBrandGoogleDrive,
	IconBrandSlack,
	IconBrandDiscord,
	IconBrandNotion,
	IconPlugConnected,
	IconPlugOff,
	IconPlus,
	IconCloud,
	IconBrandTrello,
	IconChartPie,
	IconBrain,
	IconBrandGithub,
	IconNews,
	IconFileText,
	IconPresentation,
	IconTable,
	IconMapPin,
	IconShoppingCart,
	IconX,
	IconMail,
	IconBrandWhatsapp,
	IconUsers,
	IconHelpCircle,
	IconCalendarEvent,
	IconWorldSearch
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { usePostHog } from "posthog-js/react"
import { motion, AnimatePresence } from "framer-motion"
import {
	MorphingDialog,
	MorphingDialogTrigger,
	MorphingDialogContent,
	MorphingDialogTitle,
	MorphingDialogSubtitle,
	MorphingDialogClose,
	MorphingDialogDescription,
	MorphingDialogContainer
} from "@components/ui/morphing-dialog"
import { Tooltip } from "react-tooltip"

import IconBrandTodoist from "@components/icons/IconBrandTodoist"

const HelpTooltip = ({ content }) => (
	<div className="fixed bottom-6 left-6 z-40">
		<button
			data-tooltip-id="page-help-tooltip"
			data-tooltip-content={content}
			className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
		>
			<IconHelpCircle size={22} />
		</button>
	</div>
)

const integrationIcons = {
	gmail: IconMail,
	gcalendar: IconCalendarEvent,
	gpeople: IconUsers,
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
	trello: IconBrandTrello,
	github: IconBrandGithub,
	news: IconNews,
	todoist: IconBrandTodoist,
	discord: IconBrandDiscord,
	evernote: IconFileText,
	whatsapp: IconBrandWhatsapp
}

const MANUAL_INTEGRATION_CONFIGS = {} // Manual integrations removed for Slack and Notion

const ManualTokenEntryModal = ({ integration, onClose, onSuccess }) => {
	const [credentials, setCredentials] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)
	const posthog = usePostHog()

	if (!integration) return null

	const config = MANUAL_INTEGRATION_CONFIGS[integration?.name]
	const instructions = config?.instructions || []
	const fields = config?.fields || []

	if (fields.length === 0) return null

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

			posthog?.capture("integration_connected", {
				integration_name: integration.name,
				auth_type: "manual"
			})
			toast.success(`${integration.display_name} connected successfully!`)
			onSuccess()
			onClose()
		} catch (error) {
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

const WhatsAppConnectModal = ({ integration, onClose, onSuccess }) => {
	const [number, setNumber] = useState("")
	const [isSubmitting, setIsSubmitting] = useState(false)
	const posthog = usePostHog()

	if (!integration) return null

	const handleSubmit = async () => {
		if (!number.trim()) {
			toast.error("Please provide a valid WhatsApp number.")
			return
		}

		setIsSubmitting(true)
		try {
			const response = await fetch("/api/settings/whatsapp-mcp", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ whatsapp_mcp_number: number })
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(
					data.detail || "Failed to connect WhatsApp Agent"
				)
			}
			posthog?.capture("integration_connected", {
				integration_name: "whatsapp",
				auth_type: "manual"
			})
			toast.success("WhatsApp Agent connected successfully!")
			onSuccess()
			onClose()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const modalContent = (
		<div className="text-left space-y-4 my-4">
			<p className="text-sm text-gray-400">
				Enter your WhatsApp number including the country code (e.g.,
				+14155552671). This number will be used by the agent to send
				messages on your behalf as a tool.
			</p>
			<input
				type="tel"
				value={number}
				onChange={(e) => setNumber(e.target.value)}
				placeholder="+14155552671"
				className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
				autoComplete="off"
			/>
		</div>
	)

	return (
		<ModalDialog
			title={`Connect to ${integration.display_name}`}
			description="Connect a number for the agent to use as a tool."
			onConfirm={handleSubmit}
			onCancel={onClose}
			confirmButtonText={isSubmitting ? "Connecting..." : "Connect"}
			isConfirmDisabled={isSubmitting}
			extraContent={modalContent}
		/>
	)
}

const FilterInputSection = ({
	title,
	description,
	items,
	onAdd,
	onDelete,
	placeholder
}) => {
	const [inputValue, setInputValue] = useState("")

	const handleAdd = () => {
		if (inputValue.trim()) {
			onAdd(inputValue)
			setInputValue("")
		}
	}

	return (
		<div className="bg-[var(--color-primary-surface)]/50 p-4 rounded-lg border border-[var(--color-primary-surface-elevated)]">
			<h4 className="text-md font-semibold text-gray-200 mb-1">
				{title}
			</h4>
			{description && (
				<p className="text-gray-400 text-xs mb-3">{description}</p>
			)}
			<div className="flex flex-col sm:flex-row gap-2 mb-4">
				<input
					type="text"
					value={inputValue}
					onChange={(e) => setInputValue(e.target.value)}
					onKeyDown={(e) => e.key === "Enter" && handleAdd()}
					placeholder={placeholder}
					className="flex-grow bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)] w-full"
				/>
				<button
					onClick={handleAdd}
					className="flex flex-row items-center justify-center py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors"
				>
					<IconPlus className="w-4 h-4 mr-2" /> Add
				</button>
			</div>
			<div className="flex flex-wrap gap-2">
				{items.length > 0 ? (
					items.map((item, index) => (
						<div
							key={index}
							className="flex items-center gap-2 bg-[var(--color-primary-surface-elevated)] rounded-full py-1.5 px-3 text-sm text-gray-200"
						>
							<span>{item}</span>
							<button onClick={() => onDelete(item)}>
								<IconX
									size={14}
									className="text-gray-500 hover:text-red-400"
								/>
							</button>
						</div>
					))
				) : (
					<p className="text-sm text-gray-500">
						No filters added yet.
					</p>
				)}
			</div>
		</div>
	)
}

const PrivacySettings = ({ serviceName }) => {
	const [filters, setFilters] = useState({
		keywords: [],
		emails: [],
		labels: []
	})
	const [isLoading, setIsLoading] = useState(true)

	const fetchFilters = useCallback(async () => {
		setIsLoading(true)
		try {
			const response = await fetch(
				`/api/settings/privacy-filters?service=${serviceName}`
			)
			if (!response.ok) throw new Error("Failed to fetch filters.")
			const data = await response.json()
			setFilters(data.filters)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [serviceName])

	useEffect(() => {
		fetchFilters()
	}, [fetchFilters])

	const handleSaveFilters = async (updatedFilters) => {
		setIsLoading(true)
		try {
			const response = await fetch("/api/settings/privacy-filters", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					service: serviceName,
					filters: updatedFilters
				})
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

	const handleAddItem = (type, value) => {
		if (!filters[type].includes(value)) {
			const updatedFilters = {
				...filters,
				[type]: [...filters[type], value]
			}
			handleSaveFilters(updatedFilters)
		}
	}

	const handleDeleteItem = (type, value) => {
		const updatedFilters = {
			...filters,
			[type]: filters[type].filter((item) => item !== value)
		}
		handleSaveFilters(updatedFilters)
	}

	if (isLoading) {
		return (
			<div className="flex justify-center p-8">
				<IconLoader className="w-6 h-6 animate-spin text-[var(--color-accent-blue)]" />
			</div>
		)
	}

	return (
		<div className="space-y-6">
			<FilterInputSection
				title="Keyword Filters"
				description="Emails or events containing these keywords will be ignored by the proactive memory pipeline."
				items={filters.keywords}
				onAdd={(value) => handleAddItem("keywords", value)}
				onDelete={(value) => handleDeleteItem("keywords", value)}
				placeholder="Add a new keyword..."
			/>

			{serviceName === "gmail" && (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
					<FilterInputSection
						title="Blocked Senders"
						description="Emails from these addresses will be ignored."
						items={filters.emails}
						onAdd={(value) => handleAddItem("emails", value)}
						onDelete={(value) => handleDeleteItem("emails", value)}
						placeholder="Add an email..."
					/>
					<FilterInputSection
						title="Blocked Labels"
						description="Emails with these labels will be ignored."
						items={filters.labels}
						onAdd={(value) => handleAddItem("labels", value)}
						onDelete={(value) => handleDeleteItem("labels", value)}
						placeholder="Add a label..."
					/>
				</div>
			)}
		</div>
	)
}

const IntegrationsPage = () => {
	const [userIntegrations, setUserIntegrations] = useState([])
	const [defaultTools, setDefaultTools] = useState([])
	const [loading, setLoading] = useState(true)
	const [processingIntegration, setProcessingIntegration] = useState(null)
	const [searchQuery, setSearchQuery] = useState("")
	const [activeCategory, setActiveCategory] = useState("All")
	const [selectedIntegration, setSelectedIntegration] = useState(null)
	const [whatsAppToConnect, setWhatsAppToConnect] = useState(null)
	const posthog = usePostHog()

	const googleServices = [
		"gmail",
		"gcalendar",
		"gdrive",
		"gdocs",
		"gslides",
		"gsheets",
		"gpeople"
	]

	const fetchIntegrations = useCallback(async () => {
		setLoading(true)
		try {
			const response = await fetch("/api/settings/integrations")
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to fetch integrations")

			const integrationsWithIcons = (data.integrations || []).map(
				(ds) => ({
					...ds,
					icon: integrationIcons[ds.name] || IconSettingsCog
				})
			)

			const hiddenTools = [
				"google_search",
				"progress_updater",
				"chat_tools",
				"tasks"
			]
			const connectable = integrationsWithIcons.filter(
				(i) =>
					(i.auth_type === "oauth" || i.auth_type === "manual") &&
					!hiddenTools.includes(i.name)
			)
			const builtIn = integrationsWithIcons.filter(
				(i) =>
					i.auth_type === "builtin" && !hiddenTools.includes(i.name)
			)
			setUserIntegrations(connectable)
			setDefaultTools(builtIn)
		} catch (error) {
			toast.error(`Error fetching integrations: ${error.message}`)
		} finally {
			setLoading(false)
		}
	}, [])

		const handleTrelloConnect = (integration) => {
			const trelloApiKey = integration.client_id
			if (!trelloApiKey) {
				toast.error(
					"Trello API Key is not configured by the administrator."
				)
				return
			}

			const returnUrl = `${window.location.origin}/integrations`
			const authUrl = `https://trello.com/1/authorize?expiration=never&name=Sentient&scope=read,write&response_type=token&key=${trelloApiKey}&return_url=${encodeURIComponent(returnUrl)}&callback_method=postMessage`

			const authWindow = window.open(
				authUrl,
				"trelloAuth",
				"width=600,height=700,noopener,noreferrer"
			)

			// --- ADDED FOR DEBUGGING ---
			// This listener will log EVERY message event that comes into the window,
			// helping us see what Trello is sending back, even if it fails the security checks.
			const debugListener = (event) => {
				console.log("DEBUG: Received a postMessage event:", event)
				console.log("DEBUG: Event Origin:", event.origin)
				console.log("DEBUG: Event Data:", event.data)
			}
			window.addEventListener("message", debugListener)
			// --- END OF DEBUGGING CODE ---

			const handleMessage = async (event) => {
				// Basic security checks
				if (
					event.source !== authWindow ||
					event.origin !== "https://trello.com" ||
					!event.data
				) {
					return
				}

				const token = event.data
				// Trello tokens are 64-char hex strings
				if (token && /^[0-9a-f]{64}$/.test(token)) {
					// --- ADDED FOR DEBUGGING ---
					// Clean up both listeners once we have a valid token
					window.removeEventListener("message", debugListener)
					// --- END OF DEBUGGING CODE ---

					window.removeEventListener("message", handleMessage)
					authWindow.close()

					setProcessingIntegration("trello")
					try {
						const response = await fetch(
							"/api/settings/integrations/connect/manual",
							{
								method: "POST",
								headers: { "Content-Type": "application/json" },
								body: JSON.stringify({
									service_name: "trello",
									credentials: { token: token }
								})
							}
						)
						if (!response.ok)
							throw new Error(
								(await response.json()).error ||
									"Failed to save Trello token."
							)
						toast.success("Trello connected successfully!")
						fetchIntegrations()
					} catch (error) {
						toast.error(error.message)
					} finally {
						setProcessingIntegration(null)
					}
				}
			}

			window.addEventListener("message", handleMessage, false)
		}

	const handleConnect = (integration) => {
		if (integration.name === "whatsapp") {
			setWhatsAppToConnect(integration)
			return
		}

		if (integration.auth_type === "oauth") {
			const { name: serviceName, client_id: clientId } = integration
			if (!clientId) {
				toast.error(
					`Client ID for ${integration.display_name} is not configured.`
				)
				return
			}

			if (serviceName === "trello") {
				handleTrelloConnect(integration)
				return
			}

			const redirectUri = `${window.location.origin}/api/settings/integrations/connect/oauth/callback`
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
				gpeople: "https://www.googleapis.com/auth/contacts",
				gshopping: "https://www.googleapis.com/auth/content",
				github: "repo user",
				notion: "read_content write_content insert_content", // This is not a scope, it's just for user to know. Notion doesn't use scopes in the URL.
				slack: "channels:history,channels:read,chat:write,users:read,reactions:write"
			}
			const scope =
				scopes[serviceName] ||
				"https://www.googleapis.com/auth/userinfo.email"
			if (googleServices.includes(serviceName)) {
				authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(
					redirectUri
				)}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent&state=${serviceName}`
			} else if (serviceName === "github") {
				// For GitHub, it's safer to omit the redirect_uri and let it use the default
				// configured in the OAuth App settings to avoid mismatches.
				authUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&scope=${encodeURIComponent(scope)}&state=${serviceName}`
			} else if (serviceName === "slack") {
				authUrl = `https://slack.com/oauth/v2/authorize?client_id=${clientId}&user_scope=${encodeURIComponent(
					scope
				)}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${serviceName}`
			} else if (serviceName === "notion") {
				// Notion's `owner` parameter is important
				authUrl = `https://api.notion.com/v1/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(
					redirectUri
				)}&response_type=code&owner=user&state=${serviceName}`
			} else if (serviceName === "todoist") {
				const scope = "data:read_write"
				authUrl = `https://todoist.com/oauth/authorize?client_id=${clientId}&scope=${scope}&state=${serviceName}`
			} else if (serviceName === "discord") {
				// Scopes for Discord: identify (read user info), guilds (list servers), bot (add bot to servers), applications.commands (for slash commands)
				const scope = "identify guilds bot applications.commands"
				// Permissions for the bot to read/send messages
				const permissions = "274877908992"
				authUrl = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(
					redirectUri
				)}&response_type=code&scope=${encodeURIComponent(scope)}&permissions=${permissions}&state=${serviceName}`
			} else if (serviceName === "evernote") {
				const serviceHost = "sandbox.evernote.com" // Use sandbox for dev
				authUrl = `https://${serviceHost}/oauth2/authorize?response_type=code&client_id=${clientId}&redirect_uri=${encodeURIComponent(
					redirectUri
				)}&state=${serviceName}`
			}
			if (authUrl) window.location.href = authUrl
			else
				toast.error(
					`OAuth flow for ${integration.display_name} is not implemented.`
				)
		} else if (integration.auth_type === "manual") {
			if (MANUAL_INTEGRATION_CONFIGS[integration.name]) {
			} else {
				toast.error(`UI for ${integration.display_name} not found.`)
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
		)
			return
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
			if (!response.ok)
				throw new Error(`Failed to disconnect ${displayName}`)
			posthog?.capture("integration_disconnected", {
				integration_name: integrationName
			})
			toast.success(`${displayName} disconnected.`)
			fetchIntegrations()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setProcessingIntegration(null)
		}
	}

	useEffect(() => {
		fetchIntegrations()
		const urlParams = new URLSearchParams(window.location.search)
		// Use `get` which returns the first value, which is fine here.
		const success = urlParams.get("integration_success")
		const error = urlParams.get("integration_error")

		if (success) {
			const capitalized =
				success.charAt(0).toUpperCase() + success.slice(1)
			posthog?.capture("integration_connected", {
				integration_name: success,
				auth_type: "oauth_redirect"
			})
			toast.success(`Successfully connected to ${capitalized}!`)
			window.history.replaceState({}, document.title, "/integrations")
		} else if (error) {
			toast.error(`Connection failed: ${error}`)
			window.history.replaceState({}, document.title, "/integrations")
		}
	}, [fetchIntegrations])

	const categories = useMemo(() => {
		const allCats = userIntegrations.map((i) => i.category).filter(Boolean)
		return ["All", ...new Set(allCats)]
	}, [userIntegrations])

	const filteredIntegrations = useMemo(() => {
		return userIntegrations.filter((integration) => {
			const matchesCategory =
				activeCategory === "All" ||
				integration.category === activeCategory
			const matchesSearch =
				searchQuery.trim() === "" ||
				integration.display_name
					.toLowerCase()
					.includes(searchQuery.toLowerCase()) ||
				integration.description
					.toLowerCase()
					.includes(searchQuery.toLowerCase())
			return matchesCategory && matchesSearch
		})
	}, [userIntegrations, searchQuery, activeCategory])

	return (
		<div className="flex-1 flex h-screen bg-dark-surface text-white overflow-x-hidden">
			<Tooltip
				id="page-help-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>
			<div className="flex-1 flex flex-col overflow-hidden relative bg-dark-surface md:pl-20 pb-16 md:pb-0">
				<header className="flex items-center justify-between p-4 sm:p-6 md:px-8 md:py-6 bg-dark-surface border-b border-[var(--color-primary-surface)] shrink-0">
					<HelpTooltip content="Connect your apps here. This allows Sentient to access information and perform actions on your behalf." />
					<div>
						<h1 className="text-3xl lg:text-4xl font-bold text-white">
							Connect Apps
						</h1>
						<p className="text-neutral-400 mt-1">
							Expand Sentient's capabilities by connecting your
							favorite tools.
						</p>
					</div>
				</header>
				<main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 custom-scrollbar">
					<div className="w-full max-w-7xl mx-auto">
						{loading ? (
							<div className="flex justify-center items-center py-20">
								<IconLoader className="w-12 h-12 animate-spin text-[var(--color-accent-blue)]" />
							</div>
						) : (
							<>
								<div className="flex flex-col md:flex-row gap-4 mb-8 sticky top-0 bg-dark-surface py-4 z-10">
									<input
										type="text"
										placeholder="Search integrations..."
										value={searchQuery}
										onChange={(e) =>
											setSearchQuery(e.target.value)
										}
										className="flex-grow bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:ring-2 focus:ring-sentient-blue"
									/>
									<div className="flex flex-wrap gap-2">
										{categories.map((category) => (
											<button
												key={category}
												onClick={() =>
													setActiveCategory(category)
												}
												className={cn(
													"px-4 py-2 rounded-full text-sm font-medium transition-colors",
													activeCategory === category
														? "bg-white text-black"
														: "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
												)}
											>
												{category}
											</button>
										))}
									</div>
								</div>
								<section>
									<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2">
										Connectable Apps
									</h2>
									<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
										<AnimatePresence>
											{filteredIntegrations.map(
												(integration) => (
													<MorphingDialog
														key={integration.name}
														transition={{
															type: "spring",
															bounce: 0.05,
															duration: 0.3
														}}
													>
														<MorphingDialogTrigger className="bg-gradient-to-br from-neutral-900 to-neutral-800/60 p-5 rounded-xl shadow-lg transition-all duration-300 border border-neutral-800/70 hover:border-sentient-blue/30 hover:-translate-y-1 flex flex-col group text-left h-full">
															<div className="flex items-start justify-between mb-4">
																{React.createElement(
																	integration.icon,
																	{
																		className:
																			"w-10 h-10 text-sentient-blue flex-shrink-0"
																	}
																)}
																<span
																	className={cn(
																		"px-2 py-0.5 rounded-full text-xs font-semibold",
																		integration.connected
																			? "bg-green-500/20 text-green-300"
																			: "bg-neutral-600/50 text-neutral-300"
																	)}
																>
																	{integration.connected
																		? "Connected"
																		: "Not Connected"}
																</span>
															</div>
															<div className="flex-grow">
																<MorphingDialogTitle className="font-semibold text-white text-lg">
																	{
																		integration.display_name
																	}
																</MorphingDialogTitle>
																<MorphingDialogSubtitle className="text-sm text-gray-400 mt-1 line-clamp-2">
																	{
																		integration.description
																	}
																</MorphingDialogSubtitle>
															</div>
															<div className="mt-4 flex justify-end">
																<div
																	type="button"
																	className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-neutral-700 text-neutral-400 transition-colors group-hover:bg-neutral-700 group-hover:text-white"
																	aria-label="View details"
																>
																	<IconPlus
																		size={
																			16
																		}
																	/>
																</div>
															</div>
														</MorphingDialogTrigger>
														<MorphingDialogContainer>
															<MorphingDialogContent className="pointer-events-auto relative flex h-auto w-full flex-col overflow-hidden border border-neutral-700 bg-neutral-900 sm:w-[600px] rounded-2xl">
																<div className="p-6 overflow-y-auto custom-scrollbar">
																	<div className="flex items-center gap-4 mb-4">
																		{React.createElement(
																			integration.icon,
																			{
																				className:
																					"w-10 h-10 text-sentient-blue"
																			}
																		)}
																		<div>
																			<MorphingDialogTitle className="text-2xl font-bold text-white">
																				{
																					integration.display_name
																				}
																			</MorphingDialogTitle>
																			<MorphingDialogSubtitle className="text-sm text-neutral-400">
																				{integration.connected
																					? "Connected"
																					: "Not Connected"}
																			</MorphingDialogSubtitle>
																		</div>
																	</div>
																	<MorphingDialogDescription>
																		<p className="text-neutral-300 mb-6">
																			{
																				integration.description
																			}
																		</p>
																		{[
																			"gmail",
																			"gcalendar"
																		].includes(
																			integration.name
																		) && (
																			<PrivacySettings
																				serviceName={
																					integration.name
																				}
																			/>
																		)}
																		<div className="mt-6 pt-4 border-t border-neutral-800">
																			{processingIntegration ===
																			integration.name ? (
																				<div className="flex justify-center">
																					<IconLoader className="w-6 h-6 animate-spin text-[var(--color-accent-blue)]" />
																				</div>
																			) : integration.connected ? (
																				<button
																					onClick={(
																						e
																					) => {
																						e.stopPropagation()
																						handleDisconnect(
																							integration.name
																						)
																					}}
																					className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-md bg-[var(--color-accent-red)]/20 hover:bg-[var(--color-accent-red)]/40 text-[var(--color-accent-red)] text-sm font-medium transition-colors"
																				>
																					<IconPlugOff
																						size={
																							16
																						}
																					/>
																					<span>
																						Disconnect
																					</span>
																				</button>
																			) : (
																				<button
																					onClick={(
																						e
																					) => {
																						e.stopPropagation()
																						handleConnect(
																							integration
																						)
																					}}
																					className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-md bg-[var(--color-accent-blue)]/80 hover:bg-[var(--color-accent-blue)] text-white text-sm font-medium transition-colors"
																				>
																					<IconPlugConnected
																						size={
																							16
																						}
																					/>
																					<span>
																						Connect
																					</span>
																				</button>
																			)}
																		</div>
																	</MorphingDialogDescription>
																</div>
																<MorphingDialogClose className="text-white hover:bg-neutral-700 p-1 rounded-full" />
															</MorphingDialogContent>
														</MorphingDialogContainer>
													</MorphingDialog>
												)
											)}
										</AnimatePresence>
									</div>
								</section>

								<section className="mt-12">
									<div className="flex items-center gap-2 mb-5 border-b border-[var(--color-primary-surface-elevated)] pb-2">
										<h2 className="text-xl font-semibold text-gray-300">
											Built-in Tools
										</h2>
									</div>
									<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
										{defaultTools.map((tool) => {
											const ToolIcon =
												tool.icon || IconSettingsCog
											return (
												<div
													key={tool.name}
													className="bg-[var(--color-primary-surface)]/80 p-5 rounded-xl border border-[var(--color-primary-surface-elevated)]/50"
												>
													<ToolIcon className="w-10 h-10 text-[var(--color-text-muted)] mb-4" />
													<h3 className="font-semibold text-white text-lg">
														{tool.display_name}
													</h3>
													<p className="text-sm text-gray-400 mt-1">
														{tool.description}
													</p>
												</div>
											)
										})}
									</div>
								</section>
							</>
						)}
					</div>
				</main>
			</div>
			<AnimatePresence>
				{activeManualIntegration && (
					<ManualTokenEntryModal
						integration={activeManualIntegration}
						onClose={() => setActiveManualIntegration(null)}
						onSuccess={fetchIntegrations}
					/>
				)}
				{whatsAppToConnect && (
					<WhatsAppConnectModal
						integration={whatsAppToConnect}
						onClose={() => setWhatsAppToConnect(null)}
						onSuccess={fetchIntegrations}
					/>
				)}
				{selectedIntegration && (
					<IntegrationDetailsModal
						integration={selectedIntegration}
						onClose={() => setSelectedIntegration(null)}
						onConnect={handleConnect}
						onDisconnect={handleDisconnect}
						isProcessing={
							processingIntegration === selectedIntegration?.name
						}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}

export default IntegrationsPage
