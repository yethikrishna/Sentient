"use client"
import React, { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"
import { usePostHog } from "posthog-js/react"
import { useRouter } from "next/navigation"
import {
	IconLoader,
	IconCheck,
	IconSparkles,
	IconHeart
} from "@tabler/icons-react"
import AnimatedBackground from "@components/onboarding/AnimatedBackground"
import ProgressBar from "@components/onboarding/ProgressBar"
import SparkleEffect from "@components/ui/SparkleEffect"
import { GridBackground } from "@components/ui/GridBackground"
import { UseCaseCarousel } from "@components/onboarding/UseCaseCarousel"

// --- Helper Components ---

const TypingIndicator = () => (
	<motion.div
		initial={{ opacity: 0 }}
		animate={{ opacity: 1 }}
		exit={{ opacity: 0 }}
		className="flex items-center gap-2"
	>
		<span className="text-brand-orange">[SENTIENT]:</span>
		<motion.div
			className="w-2 h-4 bg-brand-orange"
			animate={{ opacity: [0, 1, 0] }}
			transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
		/>
	</motion.div>
)

const NavigationHint = ({ onBack, onNext, isNextDisabled }) => (
	<div className="mt-6 text-center">
		{/* Mobile Buttons */}
		<div className="md:hidden flex justify-center gap-4">
			<button
				onClick={onBack}
				className="py-2 px-5 rounded-md bg-neutral-700 hover:bg-neutral-600 text-sm font-semibold"
			>
				Back
			</button>
			<button
				onClick={onNext}
				disabled={isNextDisabled}
				className="py-2 px-5 rounded-md bg-brand-orange/80 hover:bg-brand-orange text-brand-black text-sm font-semibold disabled:opacity-50"
			>
				Next
			</button>
		</div>

		{/* Desktop Hint */}
		<p className="hidden md:block text-xs text-neutral-500">
			Press{" "}
			<kbd className="px-2 py-1 text-xs font-semibold text-neutral-400 bg-neutral-800 border border-neutral-700 rounded-md">
				Enter
			</kbd>{" "}
			to continue, or{" "}
			<kbd className="px-2 py-1 text-xs font-semibold text-neutral-400 bg-neutral-800 border border-neutral-700 rounded-md">
				←
			</kbd>{" "}
			to go back.
		</p>
	</div>
)

// --- Onboarding Data ---

const questions = [
	{
		id: "user-name",
		question: "First, what should I call you?",
		type: "text-input",
		required: true,
		placeholder: "e.g., Alex"
	},
	{
		id: "timezone",
		question: "What's your timezone?",
		type: "select",
		required: true,
		options: [
			{ value: "", label: "Select your timezone..." },
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
		]
	},
	{
		id: "location",
		question: "Where are you located?",
		description:
			"This helps with local info like weather. You can type a city or detect automatically.",
		type: "location",
		required: true
	},
	{
		id: "professional-context",
		question: "What's your professional world like?",
		type: "textarea",
		required: true,
		placeholder: "e.g., I'm a software developer at a startup..."
	},
	{
		id: "personal-context",
		question: "What about your personal life and interests?",
		type: "textarea",
		required: true,
		placeholder: "e.g., I enjoy hiking, learning guitar, and soccer.",
		icon: <IconHeart />
	}
]

const sentientComments = [
	"To get started, I just need to ask a few questions to personalize your experience.",
	"Great to meet you, {user-name}! To make sure I'm always on your time...",
	"Perfect. Now, to help with local info like weather and places...",
	"This helps me understand your professional goals and context.",
	"And when you're not working? Tell me about your hobbies.",
	"Awesome! That's everything I need for now. Let's get you set up."
]

// --- Main Component ---

const OnboardingPage = () => {
	const [stage, setStage] = useState("intro") // 'intro', 'questions', 'submitting', 'complete'
	const [answers, setAnswers] = useState({})
	const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
	const [isLoading, setIsLoading] = useState(true)
	const [conversation, setConversation] = useState([])
	const [score, setScore] = useState(0)
	const [maxQuestionIndexReached, setMaxQuestionIndexReached] = useState(0)
	const [sparkleTrigger, setSparkleTrigger] = useState(0)
	const [isAiTyping, setIsAiTyping] = useState(false)
	const posthog = usePostHog()
	const router = useRouter()
	const chatEndRef = useRef(null)
	const statusChecked = useRef(false)

	const [locationState, setLocationState] = useState({
		loading: false,
		data: null,
		error: null
	})

	const addAiMessage = useCallback(
		(index) => {
			let message = sentientComments[index]
			if (message.includes("{user-name}")) {
				message = message.replace(
					"{user-name}",
					answers["user-name"] || "friend"
				)
			}
			setConversation((prev) => [
				...prev,
				{ sender: "ai", text: message }
			])
		},
		[answers]
	)

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

	const isCurrentQuestionAnswered = useCallback(() => {
		if (stage !== "questions" || currentQuestionIndex >= questions.length)
			return false
		const currentQuestion = questions[currentQuestionIndex]
		if (!currentQuestion.required) return true
		const answer = answers[currentQuestion.id]
		if (answer === undefined || answer === null || answer === "")
			return false
		if (Array.isArray(answer) && answer.length === 0) return false
		return true
	}, [answers, currentQuestionIndex, stage, questions.length])

	const handleSubmit = async () => {
		setStage("submitting")
		const mainOnboardingData = { ...answers }

		try {
			const response = await fetch("/api/onboarding", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ data: mainOnboardingData })
			})
			if (!response.ok) {
				const result = await response.json()
				throw new Error(
					result.message || "Failed to save onboarding data"
				)
			}
			posthog?.capture("onboarding_completed")
			router.push("/tasks?show_demo=true")
		} catch (error) {
			toast.error(`Error: ${error.message}`)
			setStage("questions") // Go back to questions on error
		}
	}

	const handleNext = useCallback(() => {
		if (!isCurrentQuestionAnswered() || isAiTyping) return

		// Slice conversation history to the correct point before adding the new answer.
		// This ensures that if a user goes back and changes an answer, the subsequent
		// conversation history is cleared.
		const conversationSliceIndex = 1 + currentQuestionIndex * 2
		const currentQuestion = questions[currentQuestionIndex]
		const answer = answers[currentQuestion.id]

		// Format answer for display
		let displayAnswer = answer
		if (currentQuestion.type === "location") {
			displayAnswer = locationState.data ? "Shared my location" : answer
		} else if (Array.isArray(answer)) {
			displayAnswer = answer.join(", ")
		}

		setConversation((prev) => {
			const slicedPrev = prev.slice(0, conversationSliceIndex)
			return [...slicedPrev, { sender: "user", text: displayAnswer }]
		})

		if (currentQuestionIndex >= maxQuestionIndexReached) {
			setScore((s) => s + 10)
			setMaxQuestionIndexReached(currentQuestionIndex + 1)
		}

		setSparkleTrigger((c) => c + 1)
		setIsAiTyping(true)

		setTimeout(() => {
			setIsAiTyping(false)
			if (currentQuestionIndex < questions.length - 1) {
				setCurrentQuestionIndex((prev) => prev + 1)
				addAiMessage(currentQuestionIndex + 1)
			} else {
				addAiMessage(questions.length) // Final comment
				setTimeout(handleSubmit, 1500)
			}
		}, 1500) // 1.5 second typing delay
	}, [
		currentQuestionIndex,
		answers,
		isCurrentQuestionAnswered,
		handleSubmit,
		addAiMessage,
		locationState.data,
		maxQuestionIndexReached,
		isAiTyping
	])

	const handleBack = useCallback(() => {
		if (currentQuestionIndex > 0 && !isAiTyping) {
			setCurrentQuestionIndex((prev) => {
				const newIndex = prev - 1
				// Slice conversation to remove the last user answer and the AI question that followed.
				const conversationSliceIndex = 1 + newIndex * 2
				setConversation((prevConv) =>
					prevConv.slice(0, conversationSliceIndex)
				)
				return newIndex
			})
		}
	}, [currentQuestionIndex, isAiTyping])

	// --- Effects ---

	useEffect(() => {
		if (statusChecked.current) return
		statusChecked.current = true

		const checkStatus = async () => {
			try {
				const response = await fetch("/api/user/data")
				if (!response.ok) throw new Error("Could not fetch user data.")
				const result = await response.json()
				if (result?.data?.onboardingComplete) {
					router.push("/tasks")
				} else {
					setConversation([
						{ sender: "ai", text: sentientComments[0] }
					])
					setIsLoading(false)
				}
			} catch (error) {
				toast.error(error.message)
				setIsLoading(false)
			}
		}
		checkStatus()
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [router])

	useEffect(() => {
		try {
			const userTimezone =
				Intl.DateTimeFormat().resolvedOptions().timeZone
			if (userTimezone) handleAnswer("timezone", userTimezone)
		} catch (e) {
			console.warn("Could not detect user timezone.")
		}
	}, [])

	useEffect(() => {
		const handleKeyDown = (e) => {
			if (stage === "intro" && e.key === "Enter") {
				e.preventDefault()
				setStage("questions")
			} else if (stage === "questions") {
				if (e.key === "ArrowLeft") {
					e.preventDefault()
					handleBack()
				} else if (e.key === "Enter") {
					const currentQuestion = questions[currentQuestionIndex]
					if (currentQuestion.type === "textarea" && e.shiftKey) {
						return
					}
					e.preventDefault()
					handleNext()
				}
			}
		}

		window.addEventListener("keydown", handleKeyDown)
		return () => window.removeEventListener("keydown", handleKeyDown)
	}, [stage, handleBack, handleNext, currentQuestionIndex])

	useEffect(() => {
		chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
	}, [conversation, isAiTyping])

	// --- Render Logic ---

	if (isLoading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-brand-black text-brand-white">
				<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
			</div>
		)
	}

	const renderContent = () => {
		const introVariants = {
			hidden: { opacity: 0 },
			visible: {
				opacity: 1,
				transition: {
					staggerChildren: 0.3
				}
			}
		}

		const itemVariants = {
			hidden: { y: 20, opacity: 0 },
			visible: {
				y: 0,
				opacity: 1,
				transition: { type: "spring", stiffness: 100 }
			}
		}

		switch (stage) {
			case "intro":
				return (
					<motion.div
						key="intro"
						variants={introVariants}
						initial="hidden"
						animate="visible"
						exit={{ opacity: 0, y: -20 }}
						className="text-center flex flex-col items-center"
					>
						<motion.div variants={itemVariants} className="mb-8">
							<IconSparkles
								size={80}
								className="mx-auto text-brand-orange drop-shadow-[0_0_15px_rgba(0,173,181,0.5)]"
							/>
						</motion.div>
						<motion.h1
							variants={itemVariants}
							className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 to-neutral-400"
						>
							Welcome. I'm Sentient.
						</motion.h1>
						<motion.p
							variants={itemVariants}
							className="text-lg md:text-xl text-neutral-300 max-w-xl mx-auto"
						>
							Your proactive AI, ready to get to know you.
						</motion.p>
						<motion.div
							variants={itemVariants}
							className="mt-12 flex flex-col items-center gap-4"
						>
							<motion.button
								onClick={() => {
									setStage("questions")
								}}
								className="rounded-xl bg-brand-orange px-8 py-3 text-lg font-semibold text-neutral-300 transition-colors hover:bg-opacity-80"
								whileHover={{ scale: 1.05 }}
								whileTap={{ scale: 0.95 }}
							>
								Let's Begin
							</motion.button>
						</motion.div>
					</motion.div>
				)

			case "questions":
				const currentQuestion = questions[currentQuestionIndex] ?? null
				return (
					<motion.div
						key="questions"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						className="w-full h-full flex flex-col font-mono"
					>
						<div className="pt-8 pb-4 flex-shrink-0">
							<ProgressBar
								score={score}
								totalQuestions={questions.length}
							/>
						</div>
						<div className="flex-1 w-full max-w-4xl mx-auto overflow-y-auto custom-scrollbar p-4 space-y-2 text-sm md:text-base bg-black/30 border border-brand-gray rounded-lg">
							{conversation.map((msg, index) => (
								<div key={index}>
									{msg.sender === "ai" ? (
										<p>
											<span className="text-brand-orange">
												[SENTIENT]:
											</span>
											<span className="text-brand-white">
												{" "}
												{msg.text}
											</span>
										</p>
									) : (
										<p>
											<span className="text-green-400">
												[YOU]:
											</span>
											<span className="text-neutral-300">
												{" "}
												{msg.text}
											</span>
										</p>
									)}
								</div>
							))}
							{isAiTyping && <TypingIndicator />}
							<div ref={chatEndRef} />
						</div>
						<div className="w-full max-w-4xl mx-auto p-4 flex-shrink-0">
							<AnimatePresence mode="wait">
								{currentQuestion && !isAiTyping && (
									<motion.div
										key={currentQuestionIndex}
										initial={{ opacity: 0, y: 20 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0, y: -20 }}
									>
										<div className="flex items-center gap-2">
											<span className="text-green-400">
												{">"}
											</span>
											<div className="flex-1">
												{renderInput(currentQuestion)}
											</div>
										</div>
									</motion.div>
								)}
							</AnimatePresence>
							{currentQuestion && !isAiTyping && (
								<NavigationHint
									onBack={handleBack}
									onNext={handleNext}
									isNextDisabled={
										!isCurrentQuestionAnswered()
									}
								/>
							)}
						</div>
					</motion.div>
				)

			case "submitting":
				return (
					<motion.div
						key="submitting"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						className="text-center"
					>
						<IconLoader className="w-16 h-16 animate-spin text-brand-orange mx-auto mb-6" />
						<h1 className="text-3xl font-bold">
							Personalizing your experience...
						</h1>
					</motion.div>
				)

			case "whatsNext":
				// This stage is removed as per the simplified flow.
				// The app will redirect directly after submitting.
				return null

			case "complete":
				return (
					<motion.div
						key="complete"
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						className="text-center"
					>
						<IconCheck className="w-24 h-24 text-brand-green mx-auto mb-6" />
						<h1 className="text-5xl font-bold mb-4">
							All Set, {answers["user-name"] || "Friend"}!
						</h1>
						<p className="text-xl text-neutral-400">
							Your personal AI companion is ready.
						</p>
						<p className="text-lg text-neutral-500 mt-4">
							Redirecting you to home...
						</p>
					</motion.div>
				)

			default:
				return null
		}
	}

	const renderInput = (currentQuestion) => {
		switch (currentQuestion.type) {
			case "text-input":
				return (
					<input
						type="text"
						value={answers[currentQuestion.id] || ""}
						onChange={(e) =>
							handleAnswer(currentQuestion.id, e.target.value)
						}
						placeholder={currentQuestion.placeholder}
						required={currentQuestion.required}
						autoFocus
						className="w-full px-4 py-2 bg-transparent text-brand-white placeholder:text-neutral-500 focus:ring-0 border-none p-0"
					/>
				)
			case "select":
				return (
					<select
						value={answers[currentQuestion.id] || ""}
						onChange={(e) =>
							handleAnswer(currentQuestion.id, e.target.value)
						}
						required={currentQuestion.required}
						className="w-full px-4 py-2 bg-transparent text-brand-white placeholder:text-neutral-500 focus:ring-0 border-none p-0 appearance-none"
					>
						{currentQuestion.options.map((option) => (
							<option
								key={option.value}
								value={option.value}
								disabled={option.disabled}
								className="bg-brand-gray text-brand-white"
							>
								{option.label}
							</option>
						))}
					</select>
				)
			case "textarea":
				return (
					<textarea
						value={answers[currentQuestion.id] || ""}
						onChange={(e) =>
							handleAnswer(currentQuestion.id, e.target.value)
						}
						className="w-full px-4 py-2 bg-transparent text-brand-white placeholder:text-neutral-500 focus:ring-0 border-none p-0 resize-none"
						placeholder={currentQuestion.placeholder}
						autoFocus
						rows={1}
					/>
				)
			case "location":
				return (
					<div className="flex flex-col sm:flex-row gap-4 items-start">
						<input
							type="text"
							placeholder="Or enter Locality, City, State..."
							value={
								typeof answers[currentQuestion.id] === "string"
									? answers[currentQuestion.id]
									: ""
							}
							onChange={(e) =>
								handleAnswer("location", e.target.value)
							}
							className="w-full px-4 py-2 bg-transparent text-brand-white placeholder:text-neutral-500 focus:ring-0 border-none p-0"
						/>
						<button
							type="button"
							onClick={handleGetLocation}
							disabled={locationState.loading}
							className="translate-y-3 text-sm text-center text-brand-orange hover:underline whitespace-nowrap"
						>
							{locationState.loading
								? "Detecting..."
								: "or [Detect Current Location]"}
						</button>
						{locationState.data && !isAiTyping && (
							<p className="text-sm text-green-400">
								Location captured!
							</p>
						)}
					</div>
				)
			default:
				return null
		}
	}

	return (
		<div className="grid md:grid-cols-20 min-h-screen w-full bg-brand-black text-brand-white overflow-hidden">
			{/* Left Column: Onboarding Flow */}
			<div className="relative flex flex-col items-center justify-center w-full p-4 sm:p-8 overflow-hidden md:col-span-13">
				<AnimatedBackground />
				<div className="relative z-10 w-full h-full flex flex-col items-center justify-center">
					<SparkleEffect trigger={sparkleTrigger} />
					<AnimatePresence mode="wait">
						{renderContent()}
					</AnimatePresence>
				</div>
			</div>

			{/* Right Column: Use Case Carousel (Desktop Only) */}
			<div className="hidden md:flex flex-col items-center justify-center relative md:col-span-7">
				<GridBackground>
					<motion.div
						initial={{ opacity: 0, scale: 0.9 }}
						animate={{ opacity: 1, scale: 1 }}
						transition={{
							duration: 0.5,
							delay: 0.2,
							ease: "easeOut"
						}}
					>
						<UseCaseCarousel />
					</motion.div>
				</GridBackground>
			</div>
		</div>
	)
}

export default OnboardingPage
