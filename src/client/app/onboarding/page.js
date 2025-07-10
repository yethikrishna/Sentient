"use client"
import React, { useState, useEffect, useRef } from "react"
import { motion, useSpring, useTransform, useMotionValue } from "framer-motion"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"
import { Tooltip } from "react-tooltip"
import { useSmoothScroll } from "@hooks/useSmoothScroll" // Assuming this hook exists
import {
	IconLoader,
	IconMapPin,
	IconMapPinFilled,
	IconMoodHappy,
	IconBriefcase,
	IconHeart,
	IconUser,
	IconClock,
	IconWorld,
	IconDeviceLaptop,
	IconPalette,
	IconListCheck,
	IconArrowLeft,
	IconRefresh,
	IconCheck,
	IconBrandWhatsapp,
	IconArrowRight,
	IconSparkles
} from "@tabler/icons-react"

const CheckFilled = ({ className }) => (
	<svg
		xmlns="http://www.w3.org/2000/svg"
		viewBox="0 0 24 24"
		fill="currentColor"
		className={cn("w-6 h-6 ", className)}
	>
		<path
			fillRule="evenodd"
			d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
			clipRule="evenodd"
		/>
	</svg>
)

const questionSections = {
	essentials: {
		title: "The Essentials",
		description: "Let's start with the basics to get you set up.",
		icon: <IconDeviceLaptop />
	},
	context: {
		title: "A Bit About You",
		description:
			"Help me understand your world to provide better assistance.",
		icon: <IconWorld />
	},
	personality: {
		title: "How We'll Vibe",
		description: "Let's fine-tune how we'll interact with each other.",
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
		description: "This helps me get timings right for you.",
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
		id: "whatsapp_number",
		question: "WhatsApp Number (Optional)",
		description:
			"Enter your number with country code (e.g., +14155552671) to receive notifications. You can change this later in Settings.",
		type: "text-input",
		required: false,
		placeholder: "e.g., +14155552671",
		section: "essentials",
		icon: <IconBrandWhatsapp />
	},
	{
		id: "location",
		question: "Where are you located?",
		description:
			"Share your location for local info like weather and places, or manually enter a city or address.",
		type: "location",
		section: "context",
		icon: <IconMapPin />
	},
	{
		id: "professional-context",
		question: "What's your professional world like?",
		type: "textarea",
		placeholder:
			"e.g., I'm a software developer at a startup, aiming to become a team lead. I'm focused on improving my project management skills.",
		section: "context",
		icon: <IconBriefcase />
	},
	{
		id: "personal-context",
		question: "What about your personal life and hobbies?",
		type: "textarea",
		placeholder:
			"e.g., I enjoy hiking on weekends, I'm learning to play the guitar, and I follow European soccer.",
		section: "context",
		icon: <IconHeart />
	},
	{
		id: "communication-style",
		question: "How would you like me to communicate with you?",
		description: "Choose the tone that feels most natural to you.",
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
		question:
			"What are your top priorities in life right now? (Select up to 3)",
		description: "This helps me understand what matters most to you.",
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

const GlitchTitle = ({ text }) => {
	const [animatedText, setAnimatedText] = useState(text)
	const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

	useEffect(() => {
		let interval = null
		let iteration = 0

		interval = setInterval(() => {
			setAnimatedText(
				text
					.split("")
					.map((letter, index) => {
						if (index < iteration) {
							return text[index]
						}
						return letters[Math.floor(Math.random() * 26)]
					})
					.join("")
			)

			if (iteration >= text.length) {
				clearInterval(interval)
			}
			iteration += 1 / 3
		}, 40)

		return () => clearInterval(interval)
	}, [text])

	return (
		<h1 className="text-3xl sm:text-4xl font-bold mb-3 font-mono tracking-wide">
			{animatedText}
		</h1>
	)
}

const OnboardingForm = () => {
	const [answers, setAnswers] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [submissionComplete, setSubmissionComplete] = useState(false)
	const router = useRouter()
	const [isLoading, setIsLoading] = useState(true)
	const scrollRef = useRef(null)
	useSmoothScroll(scrollRef)

	const [locationState, setLocationState] = useState({
		loading: false,
		data: null,
		error: null
	})

	useEffect(() => {
		// Pre-set timezone if possible
		try {
			const userTimezone =
				Intl.DateTimeFormat().resolvedOptions().timeZone
			if (userTimezone) {
				handleAnswer("timezone", userTimezone)
			}
		} catch (e) {
			console.warn("Could not detect user timezone.")
		}

		const checkOnboardingStatus = async () => {
			try {
				const response = await fetch("/api/user/data")
				if (!response.ok) throw new Error("Could not fetch user data.")
				const result = await response.json()
				if (result?.data?.onboardingComplete) {
					router.push("/home")
				} else {
					setIsLoading(false)
				}
			} catch (error) {
				toast.error(error.message)
				setIsLoading(false)
			}
		}
		checkOnboardingStatus()
	}, [router])

	const handleManualLocationInput = (value) => {
		handleAnswer("location", value)
		setLocationState({ loading: false, data: null, error: null }) // Clear auto-location state
	}

	const handleAnswer = (questionId, answer) => {
		setAnswers((prev) => ({ ...prev, [questionId]: answer }))
	}

	const handleMultiChoice = (questionId, option) => {
		const currentAnswers = answers[questionId] || []
		const limit = questions.find((q) => q.id === questionId)?.limit || 1
		let newAnswers
		if (currentAnswers.includes(option)) {
			newAnswers = currentAnswers.filter((item) => item !== option)
		} else {
			if (currentAnswers.length < limit) {
				newAnswers = [...currentAnswers, option]
			} else {
				toast.error(`You can select up to ${limit} options.`)
				newAnswers = currentAnswers
			}
		}
		setAnswers((prev) => ({ ...prev, [questionId]: newAnswers }))
	}

	const handleGetLocation = () => {
		if (navigator.geolocation) {
			setLocationState({ loading: true, data: null, error: null })
			navigator.geolocation.getCurrentPosition(
				(position) => {
					const { latitude, longitude } = position.coords
					const locationData = { latitude, longitude }
					setLocationState({
						loading: false,
						data: locationData,
						error: null
					})
					handleAnswer("location", locationData)
				},
				(error) => {
					setLocationState({
						loading: false,
						data: null,
						error: error.message
					})
					toast.error(`Could not get location: ${error.message}`)
				}
			)
		}
	}

	const handleSubmit = async (e) => {
		e.preventDefault()
		setIsSubmitting(true)

		// Separate WhatsApp logic to run after main onboarding
		const whatsappNumber = answers["whatsapp_number"]
		const mainOnboardingData = { ...answers }
		delete mainOnboardingData["whatsapp_number"]

		try {
			const response = await fetch("/api/onboarding", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ data: mainOnboardingData })
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(
					result.message || "Failed to save onboarding data"
				)
			}

			// After main onboarding succeeds, try to set WhatsApp number if provided
			if (whatsappNumber && whatsappNumber.trim()) {
				try {
					const waResponse = await fetch("/api/settings/whatsapp", {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							whatsapp_number: whatsappNumber
						})
					})
					if (!waResponse.ok) {
						const waError = await waResponse.json()
						// Show a non-blocking error for WhatsApp setup
						toast.error(
							`Onboarding saved, but WhatsApp setup failed: ${waError.error}`
						)
					}
				} catch (waError) {
					toast.error(
						`Onboarding saved, but could not set WhatsApp number: ${waError.message}`
					)
				}
			}

			setSubmissionComplete(true)
			setTimeout(() => router.push("/home"), 2000)
		} catch (error) {
			toast.error(`Error: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	const isFormValid = () => {
		return questions
			.filter((q) => q.required)
			.every(
				(q) =>
					answers[q.id] &&
					(Array.isArray(answers[q.id])
						? answers[q.id].length > 0
						: typeof answers[q.id] === "string"
							? answers[q.id].trim() !== ""
							: true) // For location object, just check if it exists
			)
	}

	if (isLoading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-primary-background)]">
				<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
			</div>
		)
	}
	if (submissionComplete) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-primary-background)] p-4">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="text-center"
				>
					<CheckFilled className="w-24 h-24 text-[var(--color-accent-green)] mx-auto mb-6" />
					<h1 className="text-4xl font-bold mb-4">
						All Set, {answers["user-name"] || "Friend"}!
					</h1>
					<p className="text-lg text-[var(--color-text-secondary)]">
						Your personal AI companion is ready.
					</p>
					<p className="text-md text-[var(--color-text-muted)] mt-2">
						Redirecting you to home...
					</p>
				</motion.div>
			</div>
		)
	}

	return (
		<div
			ref={scrollRef}
			className="min-h-screen w-full bg-gradient-to-br from-[var(--color-primary-background)] via-[var(--color-primary-background)] to-[var(--color-primary-surface)]/20 text-[var(--color-text-primary)] p-4 sm:p-6 flex flex-col items-center justify-start overflow-y-auto custom-scrollbar"
		>
			<Tooltip id="onboarding-tooltip" />
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="w-full max-w-3xl mx-auto"
			>
				<div className="text-center my-12 md:my-16">
					<GlitchTitle text="Welcome to Sentient" />
					<p className="text-lg text-[var(--color-text-secondary)]">
						A few questions to personalize your experience.
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-16">
					{Object.entries(questionSections).map(
						([key, { title, description }]) => (
							<section key={key}>
								<h2 className="text-2xl font-semibold border-b border-[var(--color-primary-surface-elevated)] pb-4 mb-2 flex items-center gap-3">
									<span className="text-blue-400">
										{questionSections[key].icon}
									</span>
									{title}
								</h2>
								<p className="text-base text-[var(--color-text-secondary)] mb-8">
									{description}
								</p>
								<div className="space-y-8">
									{questions
										.filter((q) => q.section === key)
										.map((q, q_idx) => (
											<motion.div
												key={q.id}
												initial={{ opacity: 0, x: -20 }}
												whileInView={{
													opacity: 1,
													x: 0
												}}
												viewport={{
													once: true,
													amount: 0.3
												}}
												transition={{
													duration: 0.5,
													delay: q_idx * 0.1
												}}
											>
												<label className="block text-lg font-semibold mb-2 flex items-center gap-3">
													<span className="text-gray-500">
														{q.icon}
													</span>
													{q.question}
												</label>
												{q.description && (
													<p className="text-sm text-[var(--color-text-secondary)] mb-4">
														{q.description}
													</p>
												)}
												{
													/* Render inputs based on type */
													(() => {
														switch (q.type) {
															case "text-input":
																return (
																	<div className="relative w-full">
																		{q.id ===
																			"whatsapp_number" && (
																			<IconBrandWhatsapp
																				className="absolute left-3 top-1/2 -translate-y-1/2 text-green-500"
																				size={
																					20
																				}
																			/>
																		)}
																		<input
																			type="text"
																			value={
																				answers[
																					q
																						.id
																				] ||
																				""
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
																			className={cn(
																				"w-full py-3 rounded-xl bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]/50 placeholder:text-[var(--color-text-muted)] transition-all",
																				q.id ===
																					"whatsapp_number"
																					? "pl-10 pr-4"
																					: "px-4"
																			)}
																			placeholder={
																				q.placeholder
																			}
																			required={
																				q.required
																			}
																		/>
																	</div>
																)
															case "select":
																return (
																	<select
																		value={
																			answers[
																				q
																					.id
																			] ||
																			""
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
																		className="w-full px-4 py-3 rounded-xl bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]/50 appearance-none"
																		required={
																			q.required
																		}
																	>
																		{q.options.map(
																			(
																				option
																			) => (
																				<option
																					key={
																						option.value
																					}
																					value={
																						option.value
																					}
																					disabled={
																						option.disabled
																					}
																					className="text-black bg-white"
																				>
																					{
																						option.label
																					}
																				</option>
																			)
																		)}
																	</select>
																)
															case "textarea":
																return (
																	<textarea
																		value={
																			answers[
																				q
																					.id
																			] ||
																			""
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
																		className="w-full px-4 py-3 rounded-xl bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]/50 placeholder:text-[var(--color-text-muted)] min-h-[120px] resize-y"
																		placeholder={
																			q.placeholder
																		}
																	/>
																)
															case "location":
																return (
																	<div className="flex flex-col sm:flex-row items-center gap-4">
																		<button
																			type="button"
																			onClick={
																				handleGetLocation
																			}
																			disabled={
																				locationState.loading
																			}
																			className="flex items-center gap-2 px-3 py-3 rounded-xl bg-[var(--color-primary-surface-elevated)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary-surface)] transition-colors disabled:opacity-50 min-w-1/3 sm:w-auto"
																		>
																			{locationState.loading ? (
																				<IconLoader
																					className="animate-spin"
																					size={
																						20
																					}
																				/>
																			) : (
																				<IconMapPin
																					size={
																						20
																					}
																				/>
																			)}
																			<span>
																				{locationState.loading
																					? "Getting Location..."
																					: "Share Current Location"}
																			</span>
																		</button>
																		<span className="hidden sm:inline text-[var(--color-text-muted)] text-sm">
																			OR
																		</span>
																		<input
																			type="text"
																			placeholder="Enter Locality, City, State, Country."
																			value={
																				typeof answers[
																					q
																						.id
																				] ===
																				"string"
																					? answers[
																							q
																								.id
																						]
																					: ""
																			}
																			onChange={(
																				e
																			) =>
																				handleManualLocationInput(
																					e
																						.target
																						.value
																				)
																			}
																			className="w-full py-3 px-4 rounded-xl bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]/50 placeholder:text-[var(--color-text-muted)] transition-all"
																		/>
																		{locationState.data &&
																			!locationState.loading && (
																				<div className="flex items-center gap-2 text-[var(--color-accent-green)]">
																					<IconMapPinFilled
																						size={
																							20
																						}
																					/>
																					<span>
																						Location
																						captured!
																					</span>
																				</div>
																			)}
																	</div>
																)
															case "single-choice":
																return (
																	<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
																		{q.options.map(
																			(
																				option
																			) => (
																				<button
																					type="button"
																					key={
																						option
																					}
																					onClick={() =>
																						handleAnswer(
																							q.id,
																							option
																						)
																					}
																					className={cn(
																						"p-4 rounded-xl border-2 text-center font-semibold transition-all duration-200",
																						answers[
																							q
																								.id
																						] ===
																							option
																							? "bg-[var(--color-accent-blue)] border-[var(--color-accent-blue)] text-white"
																							: "bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 border-[var(--color-primary-surface-elevated)] hover:border-blue-500/30"
																					)}
																				>
																					{
																						option
																					}
																				</button>
																			)
																		)}
																	</div>
																)
															case "multi-choice":
																return (
																	<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
																		{q.options.map(
																			(
																				option
																			) => (
																				<button
																					type="button"
																					key={
																						option
																					}
																					onClick={() =>
																						handleMultiChoice(
																							q.id,
																							option
																						)
																					}
																					className={cn(
																						"p-4 rounded-xl border-2 text-center font-semibold transition-all duration-200 flex items-center justify-center gap-2",
																						(
																							answers[
																								q
																									.id
																							] ||
																							[]
																						).includes(
																							option
																						)
																							? "bg-[var(--color-accent-blue)] border-[var(--color-accent-blue)] text-white"
																							: "bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 border-[var(--color-primary-surface-elevated)] hover:border-blue-500/30"
																					)}
																				>
																					{(
																						answers[
																							q
																								.id
																						] ||
																						[]
																					).includes(
																						option
																					) && (
																						<IconCheck
																							size={
																								18
																							}
																						/>
																					)}
																					{
																						option
																					}
																				</button>
																			)
																		)}
																	</div>
																)
															default:
																return null
														}
													})()
												}
											</motion.div>
										))}
								</div>
							</section>
						)
					)}

					<div className="flex justify-end pt-8 border-t border-[var(--color-primary-surface-elevated)]">
						<button
							type="submit"
							disabled={!isFormValid() || isSubmitting}
							className="w-full sm:w-auto px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-300 bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white disabled:bg-neutral-700 disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed flex items-center justify-center gap-3 shadow-lg shadow-[var(--color-accent-blue)]/10 hover:shadow-[var(--color-accent-blue)]/20"
						>
							{isSubmitting ? "Saving..." : "Save & Finish"}
						</button>
					</div>
				</form>
			</motion.div>
		</div>
	)
}

export default OnboardingForm
