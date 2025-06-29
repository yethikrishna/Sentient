"use client"
import React, { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"
import { Tooltip } from "react-tooltip"
import {
	IconLoader,
	IconMapPin,
	IconMapPinFilled,
	IconMoodHappy,
	IconTie,
	IconArrowRight,
	IconSparkles,
	IconCheck
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
		description: "Let's start with the basics to get you set up."
	},
	context: {
		title: "A Bit About You",
		description:
			"Help me understand your world to provide better assistance."
	},
	personality: {
		title: "How We'll Vibe",
		description: "Let's fine-tune how we'll interact with each other."
	}
}

const questions = [
	{
		id: "user-name",
		question: "First, what should I call you?",
		type: "text-input",
		required: true,
		placeholder: "e.g., Alex",
		section: "essentials"
	},
	{
		id: "timezone",
		question: "And what's your timezone?",
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
		section: "essentials"
	},
	{
		id: "location",
		question: "Where are you located?",
		description:
			"Optionally, share your location for local info like weather and places. You can skip this if you're not comfortable sharing.",
		type: "location-input",
		section: "context"
	},
	{
		id: "professional-context",
		question:
			"To help me assist you better, what's your professional world like?",
		type: "textarea",
		placeholder:
			"e.g., I'm a software developer at a startup, aiming to become a team lead. I'm focused on improving my project management skills.",
		section: "context"
	},
	{
		id: "personal-context",
		question:
			"And what about your personal life? What are some of your hobbies or interests?",
		type: "textarea",
		placeholder:
			"e.g., I enjoy hiking on weekends, I'm learning to play the guitar, and I follow European soccer.",
		section: "context"
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
		section: "personality"
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
		section: "personality"
	}
]

const OnboardingForm = () => {
	const [answers, setAnswers] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [submissionComplete, setSubmissionComplete] = useState(false)
	const router = useRouter()
	const [isLoading, setIsLoading] = useState(true)
	const [locationState, setLocationState] = useState({
		loading: false,
		data: null,
		error: null
	})

	useEffect(() => {
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
		try {
			const response = await fetch("/api/onboarding", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ data: answers })
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(
					result.message || "Failed to save onboarding data"
				)
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
						: true)
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
		<div className="min-h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] p-4 sm:p-6 flex items-center justify-center">
			<Tooltip id="onboarding-tooltip" />
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="w-full max-w-2xl mx-auto"
			>
				<div className="text-center mb-12">
					<h1 className="text-3xl sm:text-4xl font-bold mb-3">
						Welcome to Sentient
					</h1>
					<p className="text-lg text-[var(--color-text-secondary)]">
						A few questions to personalize your experience.
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-12">
					{Object.entries(questionSections).map(
						([key, { title, description }]) => (
							<section key={key}>
								<h2 className="text-2xl font-semibold border-b border-[var(--color-primary-surface-elevated)] pb-3 mb-1">
									{title}
								</h2>
								<p className="text-base text-[var(--color-text-secondary)] mb-8">
									{description}
								</p>
								<div className="space-y-8">
									{questions
										.filter((q) => q.section === key)
										.map((q) => (
											<div key={q.id}>
												<label className="block text-lg font-semibold mb-2">
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
																		className="w-full px-4 py-3 rounded-lg bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)] placeholder:text-[var(--color-text-muted)]"
																		placeholder={
																			q.placeholder
																		}
																		required={
																			q.required
																		}
																	/>
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
																		className="w-full px-4 py-3 rounded-lg bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)] appearance-none"
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
																		className="w-full px-4 py-3 rounded-lg bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)] placeholder:text-[var(--color-text-muted)] min-h-[120px] resize-y"
																		placeholder={
																			q.placeholder
																		}
																	/>
																)
															case "location-input":
																return (
																	<div className="flex items-center gap-4">
																		<button
																			type="button"
																			onClick={
																				handleGetLocation
																			}
																			disabled={
																				locationState.loading
																			}
																			className="flex items-center gap-2 px-5 py-3 rounded-lg bg-[var(--color-primary-surface-elevated)] text-[var(--color-text-primary)] hover:bg-neutral-600 transition-colors disabled:opacity-50"
																		>
																			<IconMapPin
																				size={
																					20
																				}
																			/>
																			<span>
																				{locationState.loading
																					? "Getting Location..."
																					: "Share Current Location"}
																			</span>
																		</button>
																		{locationState.data && (
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
																	<div className="grid grid-cols-2 gap-3">
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
																						"p-4 rounded-lg border-2 text-center font-semibold transition-all duration-200",
																						answers[
																							q
																								.id
																						] ===
																							option
																							? "bg-[var(--color-accent-blue)] border-[var(--color-accent-blue)] text-white"
																							: "bg-transparent border-[var(--color-primary-surface-elevated)] hover:border-neutral-500"
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
																	<div className="grid grid-cols-2 gap-3">
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
																						"p-4 rounded-lg border-2 text-center font-semibold transition-all duration-200 flex items-center justify-center gap-2",
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
																							: "bg-transparent border-[var(--color-primary-surface-elevated)] hover:border-neutral-500"
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
											</div>
										))}
								</div>
							</section>
						)
					)}

					<div className="flex justify-end pt-6 border-t border-[var(--color-primary-surface-elevated)]">
						<button
							type="submit"
							disabled={!isFormValid() || isSubmitting}
							className="w-full sm:w-auto px-8 py-3 rounded-lg text-lg font-semibold transition-colors duration-300 bg-[var(--color-accent-blue)] hover:bg-blue-700 text-white disabled:bg-neutral-600 disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
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
