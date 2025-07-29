"use client"

import toast from "react-hot-toast"
import {
	IconLoader,
	IconDeviceLaptop,
	IconWorld,
	IconPalette,
	IconUser,
	IconClock,
	IconHeart,
	IconBriefcase,
	IconMoodHappy,
	IconListCheck,
	IconMapPin,
	IconChevronDown,
	IconX,
	IconFlask,
	IconPlus,
	IconMessageChatbot,
	IconBrandWhatsapp,
	IconHelpCircle,
	IconKeyboard
} from "@tabler/icons-react"
import { useState, useEffect, useCallback } from "react"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"

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

const questionSections = {
	essentials: {
		title: "The Essentials",
		icon: <IconDeviceLaptop />
	},
	context: {
		title: "About You",
		icon: <IconWorld />
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
			{
				value: "America/St_Johns",
				label: "Newfoundland (NDT)"
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
	}
]

const WhatsAppSettings = () => {
	// State for System Notifications
	const [notificationNumber, setNotificationNumber] = useState("")
	const [isNotifLoading, setIsNotifLoading] = useState(true)
	const [isNotifSaving, setIsNotifSaving] = useState(false)

	const fetchNotificationSettings = useCallback(async () => {
		setIsNotifLoading(true)
		try {
			const response = await fetch("/api/settings/whatsapp-notifications")
			if (!response.ok)
				throw new Error(
					"Failed to fetch WhatsApp notification settings."
				)
			const data = await response.json()
			setNotificationNumber(data.whatsapp_notifications_number || "")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsNotifLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchNotificationSettings()
	}, [fetchNotificationSettings])

	const handleSaveNotifNumber = async () => {
		setIsNotifSaving(true)
		try {
			const response = await fetch(
				"/api/settings/whatsapp-notifications",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						whatsapp_notifications_number: notificationNumber
					})
				}
			)
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.detail || "Failed to save number.")
			toast.success("Notifications enabled for this number!")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsNotifSaving(false)
		}
	}

	const handleRemoveNotifNumber = async () => {
		setIsNotifSaving(true)
		try {
			const response = await fetch(
				"/api/settings/whatsapp-notifications",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ whatsapp_notifications_number: "" })
				}
			)
			if (!response.ok) throw new Error("Failed to remove number.")
			setNotificationNumber("")
			toast.success("Notification number removed.")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsNotifSaving(false)
		}
	}

	const hasNotifNumber =
		notificationNumber && notificationNumber.trim() !== ""

	return (
		<section className="space-y-8">
			{/* System Notifications */}
			<div>
				<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2">
					WhatsApp Notifications
				</h2>
				<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)]">
					<p className="text-gray-400 text-sm mb-4">
						Receive important system notifications (e.g., task
						completions) on WhatsApp. Enter your number including
						the country code (e.g., +14155552671).
					</p>
					{isNotifLoading ? (
						<div className="flex justify-center mt-4">
							<IconLoader className="w-6 h-6 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<div className="space-y-4">
							<div className="flex flex-col sm:flex-row gap-2">
								<div className="relative flex-grow">
									<IconBrandWhatsapp
										className="absolute left-3 top-1/2 -translate-y-1/2 text-green-500"
										size={20}
									/>
									<input
										type="tel"
										value={notificationNumber}
										onChange={(e) =>
											setNotificationNumber(
												e.target.value
											)
										}
										placeholder="Enter number for notifications"
										className="w-full pl-10 pr-4 bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
									/>
								</div>
								<div className="flex gap-2 justify-end">
									<button
										onClick={handleSaveNotifNumber}
										disabled={
											isNotifSaving ||
											!notificationNumber.trim()
										}
										className="flex items-center py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors"
									>
										{isNotifSaving ? (
											<IconLoader className="w-4 h-4 mr-2 animate-spin" />
										) : (
											<IconPlus className="w-4 h-4 mr-2" />
										)}{" "}
										{hasNotifNumber ? "Update" : "Save"}
									</button>
									{hasNotifNumber && (
										<button
											onClick={handleRemoveNotifNumber}
											disabled={isNotifSaving}
											className="flex items-center py-2 px-4 rounded-md bg-[var(--color-accent-red)]/80 hover:bg-[var(--color-accent-red)] text-white font-medium transition-colors"
										>
											<IconX className="w-4 h-4 mr-2" />{" "}
											Remove
										</button>
									)}
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</section>
	)
}

const ShortcutsSettings = () => {
	const shortcuts = {
		Global: [
			{ keys: ["Ctrl", "M"], description: "Open Chat" },
			{ keys: ["Ctrl", "B"], description: "Toggle Notifications" },
			{ keys: ["Esc"], description: "Close Modal / Chat" },
			{ keys: ["Ctrl", "K"], description: "Open Command Palette" }
		],
		Navigation: [
			{ keys: ["Ctrl", "H"], description: "Go to Chat" },
			{ keys: ["Ctrl", "J"], description: "Go to Notes" },
			{ keys: ["Ctrl", "A"], description: "Go to Tasks" },
			{ keys: ["Ctrl", "I"], description: "Go to Integrations" },
			{ keys: ["Ctrl", "S"], description: "Go to Settings" }
		]
	}

	return (
		<section>
			<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2 flex items-center gap-2">
				<IconKeyboard />
				Keyboard Shortcuts
			</h2>
			<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)]">
				<div className="grid grid-cols-1 md:grid-cols-2 gap-8">
					{Object.entries(shortcuts).map(([category, list]) => (
						<div key={category}>
							<h3 className="text-lg font-semibold text-[var(--color-accent-blue)] mb-4">
								{category}
							</h3>
							<div className="space-y-3">
								{list.map((shortcut) => (
									<div
										key={shortcut.description}
										className="flex justify-between items-center text-sm"
									>
										<span className="text-neutral-300">
											{shortcut.description}
										</span>
										<div className="flex items-center gap-2">
											{shortcut.keys.map((key) => (
												<kbd
													key={key}
													className="px-2 py-1.5 text-xs font-semibold text-gray-300 bg-neutral-700 border border-neutral-600 rounded-md"
												>
													{key}
												</kbd>
											))}
										</div>
									</div>
								))}
							</div>
						</div>
					))}
				</div>
			</div>
		</section>
	)
}

const TestingTools = () => {
	const [serviceName, setServiceName] = useState("gmail")
	const [eventData, setEventData] = useState(
		'{\n  "subject": "Project Alpha Kick-off",\n  "body": "Hi team, let\'s schedule a meeting for next Tuesday to discuss the Project Alpha kick-off. John, please prepare the presentation."\n}'
	)
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleSubmit = async (e) => {
		e.preventDefault()
		setIsSubmitting(true)
		let parsedData
		try {
			parsedData = JSON.parse(eventData)
		} catch (error) {
			toast.error("Invalid JSON in event data.")
			setIsSubmitting(false)
			return
		}

		try {
			const response = await fetch("/api/testing/inject-context", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					service_name: serviceName,
					event_data: parsedData
				})
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(result.error || "Failed to inject event.")
			}
			toast.success(
				`Event injected successfully! Event ID: ${result.event_id}`
			)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleServiceChange = (e) => {
		const newService = e.target.value
		setServiceName(newService)
		if (newService === "gmail") {
			setEventData(
				'{\n  "subject": "Project Alpha Kick-off",\n  "body": "Hi team, let\'s schedule a meeting for next Tuesday to discuss the Project Alpha kick-off. John, please prepare the presentation."\n}'
			)
		} else if (newService === "gcalendar") {
			setEventData(
				'{\n  "summary": "Finalize Q3 report",\n  "description": "Need to finalize the Q3 sales report with Sarah before the end of the week."\n}'
			)
		}
	}
	const [isTriggeringScheduler, setIsTriggeringScheduler] = useState(false)

	const [whatsAppNumber, setWhatsAppNumber] = useState("")
	const [isVerifying, setIsVerifying] = useState(false)
	const [isSending, setIsSending] = useState(false)
	const [verificationResult, setVerificationResult] = useState({
		status: null,
		message: ""
	})

	const handleTriggerScheduler = async () => {
		setIsTriggeringScheduler(true)
		try {
			const response = await fetch("/api/testing/trigger-scheduler", {
				method: "POST"
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(result.detail || "Failed to trigger scheduler.")
			}
			toast.success(result.message)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsTriggeringScheduler(false)
		}
	}
	const handleVerifyWhatsApp = async () => {
		if (!whatsAppNumber) {
			toast.error("Please enter a phone number to verify.")
			return
		}
		setIsVerifying(true)
		setVerificationResult({ status: null, message: "Verifying..." })
		try {
			const response = await fetch("/api/testing/whatsapp/verify", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ phone_number: whatsAppNumber })
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(result.detail || "Verification request failed.")
			}

			if (result.numberExists) {
				toast.success("Verification successful!")
				setVerificationResult({
					status: "success",
					message: `Number is valid. Chat ID: ${result.chatId}`
				})
			} else {
				toast.error("Number not found on WhatsApp.")
				setVerificationResult({
					status: "failure",
					message:
						"This phone number does not appear to be registered on WhatsApp."
				})
			}
		} catch (error) {
			toast.error(error.message)
			setVerificationResult({ status: "failure", message: error.message })
		} finally {
			setIsVerifying(false)
		}
	}

	const handleSendTestWhatsApp = async () => {
		if (!whatsAppNumber) {
			toast.error("Please enter a phone number to send a message to.")
			return
		}
		setIsSending(true)
		try {
			const response = await fetch("/api/testing/whatsapp", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ phone_number: whatsAppNumber })
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(
					result.detail || "Failed to send test notification."
				)
			}
			toast.success("Test notification sent successfully!")
		} catch (error) {
			toast.error(`Send failed: ${error.message}`)
		} finally {
			setIsSending(false)
		}
	}

	return (
		<section>
			<h2 className="text-xl font-semibold mb-5 text-gray-300 border-b border-[var(--color-primary-surface-elevated)] pb-2 flex items-center gap-2">
				<IconFlask />
				Developer Tools
			</h2>
			<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)]">
				<h3 className="font-semibold text-lg text-white mb-2">
					Inject Context Event
				</h3>
				<p className="text-gray-400 text-sm mb-4">
					Simulate a polling event by manually injecting context data
					into the processing pipeline. This is useful for testing the
					extractor and planner workers.
				</p>
				<form onSubmit={handleSubmit} className="space-y-4">
					<div>
						<label
							htmlFor="serviceName"
							className="block text-sm font-medium text-gray-300 mb-1"
						>
							Service
						</label>
						<select
							id="serviceName"
							value={serviceName}
							onChange={handleServiceChange}
							className="w-full bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
						>
							<option value="gmail">Gmail</option>
							<option value="gcalendar">Google Calendar</option>
						</select>
					</div>
					<div>
						<label
							htmlFor="eventData"
							className="block text-sm font-medium text-gray-300 mb-1"
						>
							Event Data (JSON)
						</label>
						<textarea
							id="eventData"
							value={eventData}
							onChange={(e) => setEventData(e.target.value)}
							rows={8}
							className="w-full font-mono text-xs bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
							placeholder='e.g., { "subject": "Hello", "body": "World" }'
						/>
					</div>
					<div className="flex justify-end">
						<button
							type="submit"
							disabled={isSubmitting}
							className="flex items-center py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors disabled:opacity-50"
						>
							{isSubmitting ? (
								<IconLoader className="w-5 h-5 animate-spin" />
							) : (
								"Inject Event"
							)}
						</button>
					</div>
				</form>
			</div>
			{/* WhatsApp Test Tools */}
			<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)] mt-6">
				<h3 className="font-semibold text-lg text-white mb-2">
					Test WhatsApp Integration
				</h3>
				<p className="text-gray-400 text-sm mb-4">
					Verify a phone number's existence on WhatsApp and then send
					a test message. The number must include the country code
					(e.g., +14155552671).
				</p>
				<div className="flex flex-col sm:flex-row gap-2">
					<div className="relative flex-grow">
						<IconBrandWhatsapp
							className="absolute left-3 top-1/2 -translate-y-1/2 text-green-500"
							size={20}
						/>
						<input
							type="tel"
							value={whatsAppNumber}
							onChange={(e) => {
								setWhatsAppNumber(e.target.value)
								setVerificationResult({
									status: null,
									message: ""
								}) // Reset on change
							}}
							placeholder="Enter WhatsApp Number with country code"
							className="w-full pl-10 pr-4 bg-[var(--color-primary-surface-elevated)] border border-neutral-600 rounded-md py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
						/>
					</div>
					<div className="flex gap-2 justify-end">
						<button
							onClick={handleVerifyWhatsApp}
							disabled={isVerifying || isSending}
							className="flex items-center justify-center py-2 px-4 rounded-md bg-purple-600 hover:bg-purple-500 text-white font-medium transition-colors disabled:opacity-50"
						>
							{isVerifying ? (
								<IconLoader className="w-5 h-5 animate-spin" />
							) : (
								"Verify"
							)}
						</button>
						<button
							onClick={handleSendTestWhatsApp}
							disabled={isSending || isVerifying}
							className="flex items-center justify-center py-2 px-4 rounded-md bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-medium transition-colors disabled:opacity-50"
						>
							{isSending ? (
								<IconLoader className="w-5 h-5 animate-spin" />
							) : (
								"Send Test"
							)}
						</button>
					</div>
				</div>
				{verificationResult.message && (
					<p
						className={cn(
							"text-sm mt-3",
							verificationResult.status === "success"
								? "text-green-400"
								: "text-red-400"
						)}
					>
						{verificationResult.message}
					</p>
				)}
			</div>
			{/* Scheduler Test Tool */}
			<div className="bg-[var(--color-primary-surface)]/50 p-4 md:p-6 rounded-lg border border-[var(--color-primary-surface-elevated)] mt-6">
				<h3 className="font-semibold text-lg text-white mb-2">
					Trigger Task Scheduler
				</h3>
				<p className="text-gray-400 text-sm mb-4">
					Manually run the Celery Beat scheduler task
					(`run_due_tasks`) to immediately check for and execute any
					due scheduled or recurring tasks. This is useful for testing
					without waiting for the 5-minute interval.
				</p>
				<div className="flex justify-end">
					<button
						onClick={handleTriggerScheduler}
						disabled={isTriggeringScheduler}
						className="flex items-center py-2 px-4 rounded-md bg-purple-600 hover:bg-purple-500 text-white font-medium transition-colors disabled:opacity-50"
					>
						{isTriggeringScheduler ? (
							<IconLoader className="w-5 h-5 animate-spin" />
						) : (
							"Run Scheduler Now"
						)}
					</button>
				</div>
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
								<div className="space-y-6 mt-4 pl-4 md:pl-8 border-l-2 border-[var(--color-primary-surface-elevated)]">
									{questions
										.filter((q) => q.section === key)
										.map((q) => (
											<div
												key={q.id}
												className="min-h-[68px]"
											>
												<label className="block text-sm font-medium text-gray-200 mb-2">
													{q.question}
												</label>
												{(() => {
													switch (q.type) {
														case "text-input":
															return (
																// eslint-disable-line
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
																// eslint-disable-line
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
																// eslint-disable-line
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
															const locationValue =
																formData[q.id]
															const isGpsLocation =
																typeof locationValue ===
																	"object" &&
																locationValue !==
																	null &&
																locationValue.latitude

															if (isGpsLocation) {
																return (
																	<div className="flex items-center gap-2">
																		<p className="w-full bg-[var(--color-primary-surface)] border border-neutral-700 rounded-md px-3 py-2 text-gray-300">
																			{`Lat: ${locationValue.latitude?.toFixed(
																				4
																			)}, Lon: ${locationValue.longitude?.toFixed(
																				4
																			)} (Detected)`}
																		</p>
																		<button
																			onClick={() =>
																				handleAnswer(
																					q.id,
																					""
																				)
																			}
																			className="p-2 text-gray-400 hover:text-white hover:bg-neutral-600 rounded-md"
																			title="Clear and enter manually"
																		>
																			<IconX
																				size={
																					18
																				}
																			/>
																		</button>
																	</div>
																)
															}
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
	const [profileData, setProfileData] = useState(null)
	const [isSavingProfile, setIsSavingProfile] = useState(false)

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
				preferences: {}
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
	}, [fetchData])

	const ProfileHeader = () => (
		<div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6 mb-10">
			<img
				src={profileData?.picture || "/images/half-logo-dark.svg"}
				alt="Profile"
				className="w-20 h-20 sm:w-24 sm:h-24 rounded-full border-4 border-[var(--color-primary-surface-elevated)] shadow-lg"
			/>
			<div>
				<h1 className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)]">
					{profileData?.personalInfo?.name || "Your Profile"}
				</h1>
				<p className="text-[var(--color-text-secondary)] mt-1">
					Manage your settings and how Sentient interacts with you.
				</p>
			</div>
		</div>
	)

	return (
		<div className="flex-1 flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-x-hidden">
			<Tooltip
				id="settings-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>
			<Tooltip
				id="page-help-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>
			<div className="flex-1 flex flex-col overflow-hidden relative w-full md:pl-20 pb-16 md:pb-0">
				<main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 custom-scrollbar">
					<HelpTooltip content="Customize your experience here." />
					<div className="w-full max-w-5xl mx-auto space-y-10">
						<ProfileHeader />
						<ProfileSettings
							initialData={profileData?.onboardingAnswers}
							onSave={handleSaveProfile}
							isSaving={isSavingProfile}
						/>
						<WhatsAppSettings />
						<ShortcutsSettings />
						{process.env.NEXT_PUBLIC_ENVIRONMENT !== "prod" &&
							process.env.NEXT_PUBLIC_ENVIRONMENT !== "stag" && (
								<TestingTools />
							)}
					</div>
				</main>
			</div>
		</div>
	)
}

export default ProfilePage
