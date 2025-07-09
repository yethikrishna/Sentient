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
	IconUserCircle,
	IconDeviceLaptop,
	IconWorld,
	IconPalette,
	IconPlugConnected,
	IconPlugOff,
	IconPlus,
	IconCloud,
	IconChartPie,
	IconBrain,
	IconUser,
	IconBrandGithub,
	IconNews,
	IconFileText,
	IconClock,
	IconMapPinFilled,
	IconBriefcase,
	IconHeart,
	IconMoodHappy,
	IconListCheck,
	IconPresentation,
	IconTable,
	IconMapPin,
	IconShoppingCart,
	IconChevronDown,
	IconChevronUp,
	IconX,
	IconBrandWhatsapp
} from "@tabler/icons-react"
import { useState, useEffect, useCallback } from "react"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"

const questionSections = {
	essentials: {
		title: "The Essentials",
		icon: <IconDeviceLaptop />
	},
	context: {
		title: "About You",
		icon: <IconWorld />
	},
	personality: {
		title: "AI Personality",
		icon: <IconPalette />
	}
}

const questions = [
	{
		id: "user-name",
		question: "What should I call you?",
		type: "text-input",
		required: true,
		placeholder: "e.g., Alex",
		section: "essentials",
		icon: <IconUser />
	},
	{
		id: "timezone",
		question: "What's your timezone?",
		type: "select",
		required: true,
		options: [
			{ value: "", label: "Select your timezone...", disabled: true },
			{ value: "America/New_York", label: "Eastern Time (US & Canada)" },
			{ value: "America/Chicago", label: "Central Time (US & Canada)" },
			{ value: "America/Denver", label: "Mountain Time (US & Canada)" },
			{
				value: "America/Los_Angeles",
				label: "Pacific Time (US & Canada)"
			},
			{ value: "Europe/London", label: "London, Dublin (GMT/BST)" },
			{ value: "Europe/Berlin", label: "Berlin, Paris (CET)" },
			{ value: "Asia/Kolkata", label: "India (IST)" },
			{ value: "Asia/Singapore", label: "Singapore (SGT)" },
			{ value: "UTC", label: "Coordinated Universal Time (UTC)" }
		],
		section: "essentials",
		icon: <IconClock />
	},
	{
		id: "location",
		question: "Where are you located?",
		type: "location",
		section: "context",
		icon: <IconMapPin />
	},
	{
		id: "professional-context",
		question: "What's your professional world like?",
		type: "textarea",
		placeholder:
			"e.g., I'm a software developer at a startup, aiming to become a team lead...",
		section: "context",
		icon: <IconBriefcase />
	},
	{
		id: "personal-context",
		question: "What about your personal life and hobbies?",
		type: "textarea",
		placeholder:
			"e.g., I enjoy hiking on weekends, I'm learning to play the guitar...",
		section: "context",
		icon: <IconHeart />
	},
	{
		id: "communication-style",
		question: "How would you like me to communicate with you?",
		type: "single-choice",
		required: true,
		options: [
			"Casual & Friendly",
			"Professional & Formal",
			"Concise & To-the-point",
			"Enthusiastic & Witty"
		],
		section: "personality",
		icon: <IconMoodHappy />
	},
	{
		id: "core-priorities",
		question: "What are your top priorities? (Select up to 3)",
		type: "multi-choice",
		limit: 3,
		options: [
			"Career Growth",
			"Health & Wellness",
			"Family & Relationships",
			"Learning & Personal Growth",
			"Financial Stability",
			"Hobbies & Leisure"
		],
		section: "personality",
		icon: <IconListCheck />
	}
]

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

const WhatsAppSettings = () => {
	const [whatsappNumber, setWhatsappNumber] = useState("")
	const [isLoading, setIsLoading] = useState(true)
	const [isSaving, setIsSaving] = useState(false)

	const fetchWhatsAppNumber = useCallback(async () => {
		setIsLoading(true)
		try {
			const response = await fetch("/api/settings/whatsapp")
			if (!response.ok)
				throw new Error("Failed to fetch WhatsApp number.")
			const data = await response.json()
			setWhatsappNumber(data.whatsapp_number || "")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchWhatsAppNumber()
	}, [fetchWhatsAppNumber])

	const handleSave = async () => {
		setIsSaving(true)
		try {
			const response = await fetch("/api/settings/whatsapp", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ whatsapp_number: whatsappNumber })
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to save number.")
			}
			toast.success("WhatsApp number saved successfully!")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSaving(false)
		}
	}

	const handleRemove = async () => {
		setIsSaving(true)
		try {
			const response = await fetch("/api/settings/whatsapp", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ whatsapp_number: "" }) // Send empty string to remove
			})
			if (!response.ok) throw new Error("Failed to remove number.")
			setWhatsappNumber("")
			toast.success("WhatsApp notifications disabled.")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSaving(false)
		}
	}

	return (
		<section>
			<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2">
				WhatsApp Notifications
			</h2>
			<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)]">
				<p className="text-gray-400 text-sm mb-4">
					Receive important notifications directly to your WhatsApp.
					Enter your number including the country code (e.g.,
					14155552671).
				</p>
				{isLoading ? (
					<div className="flex justify-center mt-4">
						<IconLoader className="w-6 h-6 animate-spin text-[var(--color-accent-blue)]" />
					</div>
				) : (
					<div className="flex flex-col sm:flex-row gap-2">
						<div className="relative flex-grow">
							<IconBrandWhatsapp
								className="absolute left-3 top-1/2 -translate-y-1/2 text-green-500"
								size={20}
							/>
							<input
								type="tel"
								value={whatsappNumber}
								onChange={(e) =>
									setWhatsappNumber(e.target.value)
								}
								placeholder="Enter WhatsApp Number"
								className="w-full pl-10 pr-4 bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
							/>
						</div>
						<div className="flex gap-2 justify-end">
							<button
								onClick={handleSave}
								disabled={isSaving}
								className="flex items-center py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors"
							>
								{isSaving ? (
									<IconLoader className="w-4 h-4 mr-2 animate-spin" />
								) : (
									<IconPlus className="w-4 h-4 mr-2" />
								)}
								Save
							</button>
							{whatsappNumber && (
								<button
									onClick={handleRemove}
									disabled={isSaving}
									className="flex items-center py-2 px-4 rounded-md bg-[var(--color-accent-red)]/80 hover:bg-[var(--color-accent-red)] text-white font-medium transition-colors"
								>
									<IconX className="w-4 h-4 mr-2" /> Remove
								</button>
							)}
						</div>
					</div>
				)}
			</div>
		</section>
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
						className="flex flex-row items-center py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors"
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

const ProfileSettings = ({ initialData, onSave, isSaving }) => {
	const [formData, setFormData] = useState(initialData || {})
	const [openSections, setOpenSections] = useState({
		essentials: true,
		context: true,
		personality: true
	})

	useEffect(() => {
		setFormData(initialData || {})
	}, [initialData])

	const handleAnswer = (questionId, answer) => {
		setFormData((prev) => ({ ...prev, [questionId]: answer }))
	}

	const handleMultiChoice = (questionId, option) => {
		const currentAnswers = formData[questionId] || []
		const limit = questions.find((q) => q.id === questionId)?.limit || 1
		const newAnswers = currentAnswers.includes(option)
			? currentAnswers.filter((item) => item !== option)
			: currentAnswers.length < limit
				? [...currentAnswers, option]
				: currentAnswers
		setFormData((prev) => ({ ...prev, [questionId]: newAnswers }))
	}

	return (
		<section>
			<div className="flex justify-between items-center">
				<h2 className="text-xl font-semibold text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2 flex-grow">
					About You
				</h2>
				<button
					onClick={() => onSave(formData)}
					disabled={isSaving}
					className="ml-4 py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors flex items-center"
				>
					{isSaving ? (
						<IconLoader className="w-5 h-5 animate-spin" />
					) : (
						"Save Profile"
					)}
				</button>
			</div>
			<p className="text-gray-400 text-sm mt-2 mb-6">
				This information helps me personalize my responses and actions
				for you.
			</p>

			<div className="space-y-8">
				{Object.entries(questionSections).map(
					([key, { title, icon }]) => (
						<div key={key}>
							<button
								onClick={() =>
									setOpenSections((p) => ({
										...p,
										[key]: !p[key]
									}))
								}
								className="w-full flex justify-between items-center py-2 text-left"
							>
								<h3 className="text-lg font-semibold text-gray-300 flex items-center gap-3">
									{icon}
									{title}
								</h3>
								<IconChevronDown
									className={cn(
										"transition-transform duration-200",
										openSections[key] && "rotate-180"
									)}
								/>
							</button>
							{openSections[key] && (
								<div className="space-y-6 mt-4 pl-8 border-l-2 border-[var(--color-primary-surface-elevated)]">
									{questions
										.filter((q) => q.section === key)
										.map((q) => (
											<div key={q.id}>
												<label className="block text-sm font-medium text-gray-200 mb-2">
													{q.question}
												</label>
												{(() => {
													switch (q.type) {
														case "text-input":
															return (
																<input
																	type="text"
																	value={
																		formData[
																			q.id
																		] || ""
																	}
																	onChange={(
																		e
																	) =>
																		handleAnswer(
																			q.id,
																			e
																				.target
																				.value
																		)
																	}
																	className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
																	placeholder={
																		q.placeholder
																	}
																/>
															)
														case "textarea":
															return (
																<textarea
																	value={
																		formData[
																			q.id
																		] || ""
																	}
																	onChange={(
																		e
																	) =>
																		handleAnswer(
																			q.id,
																			e
																				.target
																				.value
																		)
																	}
																	rows={3}
																	className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
																	placeholder={
																		q.placeholder
																	}
																/>
															)
														case "select":
															return (
																<select
																	value={
																		formData[
																			q.id
																		] || ""
																	}
																	onChange={(
																		e
																	) =>
																		handleAnswer(
																			q.id,
																			e
																				.target
																				.value
																		)
																	}
																	className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
																>
																	{q.options.map(
																		(
																			opt
																		) => (
																			<option
																				key={
																					opt.value
																				}
																				value={
																					opt.value
																				}
																			>
																				{
																					opt.label
																				}
																			</option>
																		)
																	)}
																</select>
															)
														case "single-choice":
														case "multi-choice":
															return (
																<div className="flex flex-wrap gap-2">
																	{q.options.map(
																		(
																			opt
																		) => (
																			<button
																				key={
																					opt
																				}
																				onClick={() =>
																					q.type ===
																					"single-choice"
																						? handleAnswer(
																								q.id,
																								opt
																							)
																						: handleMultiChoice(
																								q.id,
																								opt
																							)
																				}
																				className={cn(
																					"px-3 py-1.5 rounded-full text-sm font-medium border-2 transition-colors",
																					(
																						Array.isArray(
																							formData[
																								q
																									.id
																							]
																						)
																							? formData[
																									q
																										.id
																								].includes(
																									opt
																								)
																							: formData[
																									q
																										.id
																								] ===
																								opt
																					)
																						? "bg-[var(--color-accent-blue)] border-[var(--color-accent-blue)] text-white"
																						: "bg-transparent border-[var(--color-primary-surface-elevated)] text-gray-300 hover:border-[var(--color-accent-blue)]"
																				)}
																			>
																				{
																					opt
																				}
																			</button>
																		)
																	)}
																</div>
															)
														case "location": // Simplified for now
															return (
																<input
																	type="text"
																	value={
																		formData[
																			q.id
																		] || ""
																	}
																	onChange={(
																		e
																	) =>
																		handleAnswer(
																			q.id,
																			e
																				.target
																				.value
																		)
																	}
																	className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
																	placeholder="City, Country"
																/>
															)
														default:
															return null
													}
												})()}
											</div>
										))}
								</div>
							)}
						</div>
					)
				)}
			</div>
		</section>
	)
}

const ProfilePage = () => {
	const [userIntegrations, setUserIntegrations] = useState([])
	const [defaultTools, setDefaultTools] = useState([])
	const [loadingIntegrations, setLoadingIntegrations] = useState(true)
	const [activeManualIntegration, setActiveManualIntegration] = useState(null)
	const [processingIntegration, setProcessingIntegration] = useState(null)
	const [profileData, setProfileData] = useState(null)
	const [isSavingProfile, setIsSavingProfile] = useState(false)

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

	const handleSaveProfile = async (newOnboardingData) => {
		setIsSavingProfile(true)
		try {
			const payload = {
				onboardingAnswers: newOnboardingData,
				personalInfo: {
					name: newOnboardingData["user-name"],
					location: newOnboardingData["location"],
					timezone: newOnboardingData["timezone"]
				},
				preferences: {
					communicationStyle:
						newOnboardingData["communication-style"],
					corePriorities: newOnboardingData["core-priorities"]
				}
			}

			const response = await fetch("/api/settings/profile", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload)
			})

			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Failed to save profile")
			}
			toast.success("Profile updated successfully!")
			fetchData() // Refresh data to show changes
		} catch (error) {
			toast.error(`Error saving profile: ${error.message}`)
		} finally {
			setIsSavingProfile(false)
		}
	}

	const fetchData = useCallback(async () => {
		try {
			const [response, profileResponse] = await Promise.all([
				fetch("/api/user/data"),
				fetch("/api/user/profile")
			])
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(
					errorData.message || "Failed to fetch user data"
				)
			}
			if (!profileResponse.ok)
				throw new Error("Failed to fetch user profile")
			const result = await response.json()
			const profile = await profileResponse.json()
			if (result.data) {
				setProfileData({ ...profile, ...result.data })
			}
		} catch (error) {
			toast.error(`Failed to fetch user data: ${error.message}`)
		}
	}, [])

	useEffect(() => {
		fetchData()
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
	}, [fetchData, fetchIntegrations])

	const ProfileHeader = () => (
		<div className="flex items-center gap-6 mb-10">
			<img
				src={profileData?.picture || "/images/half-logo-dark.svg"}
				alt="Profile"
				className="w-24 h-24 rounded-full border-4 border-[var(--color-primary-surface-elevated)] shadow-lg"
			/>
			<div>
				<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)]">
					{profileData?.personalInfo?.name || "Your Profile"}
				</h1>
				<p className="text-[var(--color-text-secondary)] mt-1">
					Manage your settings and how Sentient interacts with you.
				</p>
			</div>
		</div>
	)

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="settings-tooltip" />
			<div className="flex-1 flex flex-col overflow-hidden h-screen">
				<main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 custom-scrollbar">
					<div className="w-full max-w-5xl mx-auto space-y-10">
						<ProfileHeader />
						<ProfileSettings
							initialData={profileData?.onboardingAnswers}
							onSave={handleSaveProfile}
							isSaving={isSavingProfile}
						/>
						<WhatsAppSettings />
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
															<details
																className="mt-1 text-gray-400 text-xs sm:text-sm group"
																data-tooltip-id="settings-tooltip"
																data-tooltip-content="Click to see what this integration does"
															>
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
																className="flex items-center justify-center gap-1 sm:gap-2 w-full py-2 px-3 rounded-md bg-[var(--color-accent-red)]/20 hover:bg-[var(--color-accent-red)]/40 text-[var(--color-accent-red)] text-sm font-medium transition-colors"
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
																className="flex items-center justify-center gap-1 sm:gap-2 w-full py-2 px-3 rounded-md bg-[var(--color-accent-blue)]/80 hover:bg-[var(--color-accent-blue)] text-white text-sm font-medium transition-colors"
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
							<h2
								className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2"
								data-tooltip-id="settings-tooltip"
								data-tooltip-content="These tools are core to Sentient and are always enabled."
							>
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
															<details
																className="mt-1 text-gray-400 text-xs sm:text-sm group"
																data-tooltip-id="settings-tooltip"
																data-tooltip-content="Click to see what this tool does"
															>
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

export default ProfilePage
