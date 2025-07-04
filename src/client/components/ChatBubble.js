import React from "react"
import { useState } from "react" // Importing useState hook from React for managing component state
import {
	IconClipboard, // Icon for clipboard (copy) action
	IconCheck, // Icon for checkmark (confirmation) action
	IconBrain, // Icon for brain (memory) feature
	IconSettings, // Icon for settings (agents) feature
	IconGlobe, // Icon for globe (internet) feature
	IconLink, // Icon for external link
	IconMail, // Icon for mail
	IconCode,
	IconChevronDown,
	IconChevronUp,
	IconTerminal2
} from "@tabler/icons-react" // Importing icons from tabler-icons-react library
import { Tooltip } from "react-tooltip" // Importing Tooltip component for displaying tooltips
import ReactMarkdown from "react-markdown" // Importing ReactMarkdown component for rendering Markdown content
import remarkGfm from "remark-gfm" // Importing remarkGfm plugin for ReactMarkdown to support GitHub Flavored Markdown
import IconGoogleDocs from "./icons/IconGoogleDocs" // Importing custom icon component for Google Docs
import IconGoogleSheets from "./icons/IconGoogleSheets" // Importing custom icon component for Google Sheets
import IconGoogleCalendar from "./icons/IconGoogleCalendar" // Importing custom icon component for Google Calendar
import IconGoogleSlides from "./icons/IconGoogleSlides" // Importing custom icon component for Google Slides
import IconGoogleDrive from "./icons/IconGoogleDrive" // Importing custom icon component for Google Drive
import IconGoogleMail from "./icons/IconGoogleMail" // Importing custom icon component for Google Mail
import toast from "react-hot-toast" // Importing toast for displaying toast notifications

/**
 * LinkButton Component - Renders a styled button that opens a link in a new tab.
 *
 * This component is used within chat messages to display URLs in a button format.
 * It automatically detects the type of link (e.g., Google Docs, Gmail, generic link)
 * and displays an appropriate icon and name. Clicking the button opens the link in a new tab.
 *
 * @param {object} props - Component props.
 * @param {string} props.href - The URL to be opened when the button is clicked.
 * @param {React.ReactNode} props.children - The display text for the link, used as fallback name if tool name not found.
 * @returns {React.ReactNode} - The LinkButton component UI.
 */
const LinkButton = ({ href, children }) => {
	// Mapping of domain names to their respective icons and names for tool identification
	const toolMapping = {
		"drive.google.com": {
			icon: <IconGoogleDrive size={14} className="mr-1" />,
			name: "Google Drive"
		},
		"mail.google.com": {
			icon: <IconGoogleMail size={14} className="mr-1" />,
			name: "Gmail"
		},
		"gmail.com": {
			icon: <IconGoogleMail size={14} className="mr-1" />,
			name: children // Fallback name if specific tool name is not found
		},
		"docs.google.com/spreadsheets": {
			icon: <IconGoogleSheets />,
			name: "Google Sheets"
		},
		"docs.google.com/presentation": {
			icon: <IconGoogleSlides />,
			name: "Google Slides"
		},
		"calendar.google.com": {
			icon: <IconGoogleCalendar />,
			name: "Google Calendar"
		},
		"docs.google.com": {
			icon: <IconGoogleDocs />,
			name: "Google Docs"
		},
		"external-mail": {
			icon: <IconMail size={14} className="mr-1" />,
			name: children // Uses children as name for external mail links
		},
		default: {
			icon: <IconLink size={14} className="mr-1" />,
			name: "Link" // Default name for generic links
		}
	}

	/**
	 * Determines the tool details (icon and name) based on the URL.
	 *
	 * Iterates through the `toolMapping` to find a matching domain in the given URL.
	 * If a match is found, returns the corresponding icon and name.
	 * If no specific domain is matched, defaults to a generic link icon and name.
	 *
	 * @function getToolDetails
	 * @param {string} url - The URL to analyze.
	 * @returns {{ icon: React.ReactNode, name: string }} - An object containing the icon and name for the tool.
	 */
	const getToolDetails = (url) => {
		for (const domain in toolMapping) {
			if (url.includes(domain)) {
				return toolMapping[domain] // Return tool details if domain is found in URL
			} else if (url.match(/^[^@]+@[\w.-]+\.[a-z]{2,}$/i)) {
				return toolMapping["external-mail"] // Return external mail tool details if URL matches email format
			}
		}
		return toolMapping["default"] // Return default tool details for unmatched URLs
	}

	const { icon, name } = getToolDetails(href) // Get tool icon and name based on href

	return (
		<span
			onClick={() => window.open(href, "_blank", "noopener noreferrer")}
			className="bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] hover:border-[var(--color-accent-blue)] py-1 px-2 rounded-md items-center cursor-pointer inline-flex"
			// Styling for the link button: background, text color, border, padding, rounded corners, cursor, inline-flex display
			style={{
				display: "inline-flex", // Ensure inline-flex for proper alignment
				verticalAlign: "middle" // Vertical alignment to middle
			}}
		>
			{icon} {/* Render the icon determined by getToolDetails */}
			<span>{name}</span>{" "}
			{/* Render the name determined by getToolDetails */}
		</span>
	)
}

/**
 * A dedicated component to render tool code blocks neatly.
 */
const ToolCodeBlock = ({ name, code, isExpanded, onToggle }) => {
	let formattedCode = code
	try {
		// Pretty-print if it's a JSON string
		const parsed = JSON.parse(code)
		formattedCode = JSON.stringify(parsed, null, 2)
	} catch (e) {
		// Not JSON, leave as is
	}

	return (
		<div className="mb-4 border-l-2 border-green-500 pl-3">
			<button
				onClick={onToggle}
				className="flex items-center gap-2 text-green-400 hover:text-green-300 text-sm font-semibold"
				data-tooltip-id="chat-bubble-tooltip"
				data-tooltip-content="Click to see the tool call details."
			>
				{isExpanded ? (
					<IconChevronUp size={16} />
				) : (
					<IconChevronDown size={16} />
				)}
				Tool Call: {name}
			</button>
			{isExpanded && (
				<div className="mt-2 p-3 bg-neutral-800/50 rounded-md">
					<pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono">
						<code>{formattedCode}</code>
					</pre>
				</div>
			)}
		</div>
	)
}

/**
 * A dedicated component to render tool result blocks neatly.
 * NOTE: This component is now being used to display the tool result.
 */
const ToolResultBlock = ({ name, result, isExpanded, onToggle }) => {
	let formattedResult = result
	try {
		// Pretty-print if it's a JSON string
		const parsed = JSON.parse(result)
		formattedResult = JSON.stringify(parsed, null, 2)
	} catch (e) {
		// Not a valid JSON, leave as is
	}

	return (
		<div className="mb-4 border-l-2 border-purple-500 pl-3">
			<button
				onClick={onToggle}
				className="flex items-center gap-2 text-purple-400 hover:text-purple-300 text-sm font-semibold"
				data-tooltip-id="chat-bubble-tooltip"
				data-tooltip-content="Click to see the result from the tool."
			>
				{isExpanded ? (
					<IconChevronUp size={16} />
				) : (
					<IconChevronDown size={16} />
				)}
				Tool Result: {name}
			</button>
			{isExpanded && (
				<div className="mt-2 p-3 bg-neutral-800/50 rounded-md">
					<pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono">
						<code>{formattedResult}</code>
					</pre>
				</div>
			)}
		</div>
	)
}

/**
 * ChatBubble Component - Displays a single chat message bubble.
 *
 * This component renders a chat message, distinguishing between user and AI messages with different styles.
 * It supports rendering Markdown content, detects and renders URLs as LinkButtons, and provides functionality
 * to copy message text to the clipboard. For AI messages, it also conditionally displays icons indicating
 * if memory, agents, or internet were used in generating the response, along with tooltips for these icons.
 *
 * @param {object} props - Component props.
 * @param {string} props.message - The text content of the chat message, can be Markdown or JSON.
 * @param {boolean} props.isUser - Boolean indicating if the message is from the user or AI.
 * @param {boolean} props.memoryUsed - Boolean indicating if memory was used to generate the response (AI messages only).
 * @param {boolean} props.agentsUsed - Boolean indicating if agents were used (AI messages only).
 * @param {boolean} props.boolean - Boolean indicating if internet was used (AI messages only).
 * @returns {React.ReactNode} - The ChatBubble component UI.
 */
const ChatBubble = ({
	message, // Text content of the message, can be Markdown or JSON - message: string
	isUser, // Boolean, true if message is from user, false if from AI - isUser: boolean
	memoryUsed, // Boolean, true if memory was used in response generation (AI only) - memoryUsed: boolean
	agentsUsed, // Boolean, true if agents were used in response generation (AI only) - agentsUsed: boolean
	internetUsed // Boolean, true if internet was used in response generation (AI only) - internetUsed: boolean
}) => {
	// State to manage the 'copied' status for the copy button, indicating if the message text has been copied.
	const [copied, setCopied] = useState(false)
	const [expandedStates, setExpandedStates] = useState({})

	/**
	 * Handles copying the message text to the clipboard.
	 *
	 * When the copy button is clicked, this function attempts to write the message text to the clipboard.
	 * On success, it sets the 'copied' state to true to update the button icon to a checkmark,
	 * and then resets it back to false after a short delay (2 seconds) to revert the icon.
	 * If copying fails, it displays an error toast notification to inform the user.
	 *
	 * @function handleCopyToClipboard
	 * @returns {void}
	 */
	const handleCopyToClipboard = () => {
		let textToCopy = message
		// If message is a JSON string (e.g., from old tool results), stringify it for copying
		try {
			const parsed = JSON.parse(message)
			textToCopy = JSON.stringify(parsed, null, 2)
		} catch (e) {
			// Not a JSON string, copy as is
		}

		navigator.clipboard
			.writeText(textToCopy)
			.then(() => {
				setCopied(true)
				setTimeout(() => setCopied(false), 2000)
			})
			.catch((err) => toast.error(`Failed to copy text: ${err}`))
	}

	const toggleExpansion = (id) => {
		setExpandedStates((prev) => ({ ...prev, [id]: !prev[id] }))
	}

	/**
	 * Renders the content of the chat bubble.
	 *
	 * This function parses the incoming message string for special tags like <think>,
	 * <tool_code>, and <tool_result>. It splits the message into parts and renders
	 * each part accordingly: text as Markdown, and special tags as collapsible blocks.
	 */
	const renderMessageContent = () => {
		if (isUser || typeof message !== "string" || !message) {
			// Fallback for user messages or non-string AI messages
			return (
				<ReactMarkdown
					className="prose prose-invert"
					remarkPlugins={[remarkGfm]}
					children={message || ""}
					components={{
						a: ({ href, children }) => (
							<LinkButton href={href} children={children} />
						)
					}}
				/>
			)
		}

		const contentParts = []
		const regex =
			/(<think>[\s\S]*?<\/think>|<tool_code name="[^"]+">[\s\S]*?<\/tool_code>|<tool_result tool_name="[^"]+">[\s\S]*?<\/tool_result>)/g
		let lastIndex = 0

		// --- START OF THE ROBUST FIX ---

		// Helper function to check for and filter out junk tokens
		const isJunk = (text) => {
			const trimmed = text.trim()
			if (trimmed === "") return true // Ignore whitespace-only strings

			// This regex identifies common junk patterns seen in logs.
			// It looks for fragments of closing tags or orphaned tag-like words.
			const junkRegex = /^(<\/(\w+>)?|_code>|code>|ode>|>)$/
			return junkRegex.test(trimmed)
		}

		for (const match of message.matchAll(regex)) {
			// 1. Process the text *before* the current valid tag
			if (match.index > lastIndex) {
				const textContent = message.substring(lastIndex, match.index)
				// Only add the text if it's NOT junk
				if (!isJunk(textContent)) {
					contentParts.push({ type: "text", content: textContent })
				}
			}

			// 2. Process the valid, complete tag itself
			const tag = match[0]
			let subMatch

			if (
				(subMatch = tag.match(
					/<tool_code name="([^"]+)">([\s\S]*?)<\/tool_code>/
				))
			) {
				const toolName = subMatch[1]
				// Handle empty tool_code blocks gracefully
				const toolCode = subMatch[2] ? subMatch[2].trim() : "{}"
				contentParts.push({
					type: "tool_code",
					name: toolName,
					code: toolCode
				})
			} else if (
				(subMatch = tag.match(
					/<tool_result tool_name="([^"]+)">([\s\S]*?)<\/tool_result>/
				))
			) {
				const toolName = subMatch[1]
				const toolResult = subMatch[2] ? subMatch[2].trim() : "{}"
				contentParts.push({
					type: "tool_result",
					name: toolName,
					result: toolResult
				})
			} else if ((subMatch = tag.match(/<think>([\s\S]*?)<\/think>/))) {
				const thinkContent = subMatch[1].trim()
				if (thinkContent) {
					contentParts.push({
						type: "think",
						content: thinkContent
					})
				}
			}

			// 3. Update our position in the message string
			lastIndex = match.index + tag.length
		}

		// 4. Process any remaining text after the last valid tag
		if (lastIndex < message.length) {
			const remainingText = message.substring(lastIndex)
			// Also check the final part for junk or incomplete streaming tags
			const openBrackets = (message.match(/</g) || []).length
			const closeBrackets = (message.match(/>/g) || []).length

			if (!isJunk(remainingText) && openBrackets <= closeBrackets) {
				contentParts.push({ type: "text", content: remainingText })
			}
		}
		// --- END OF THE ROBUST FIX ---

		// The rest of the rendering logic remains the same
		return contentParts.map((part, index) => {
			const partId = `${part.type}_${index}`
			if (part.type === "think" && part.content) {
				return (
					<div
						key={partId}
						className="mb-4 border-l-2 border-yellow-500 pl-3"
					>
						<button
							onClick={() => toggleExpansion(partId)}
							className="flex items-center gap-2 text-yellow-400 hover:text-yellow-300 text-sm font-semibold"
							data-tooltip-id="chat-bubble-tooltip"
							data-tooltip-content="Click to see the agent's internal reasoning for this step."
						>
							{expandedStates[partId] ? (
								<IconChevronUp size={16} />
							) : (
								<IconChevronDown size={16} />
							)}
							Agent's Thought Process
						</button>
						{expandedStates[partId] && (
							<div className="mt-2 p-3 bg-neutral-800/50 rounded-md">
								<ReactMarkdown className="prose prose-sm prose-invert text-gray-300 whitespace-pre-wrap">
									{part.content}
								</ReactMarkdown>
							</div>
						)}
					</div>
				)
			}
			if (part.type === "tool_code") {
				return (
					<ToolCodeBlock
						key={partId}
						name={part.name}
						code={part.code}
						isExpanded={!!expandedStates[partId]}
						onToggle={() => toggleExpansion(partId)}
					/>
				)
			}
			// ADDED THIS BLOCK TO RENDER THE TOOL RESULT
			if (part.type === "tool_result") {
				return (
					<ToolResultBlock
						key={partId}
						name={part.name}
						result={part.result}
						isExpanded={!!expandedStates[partId]}
						onToggle={() => toggleExpansion(partId)}
					/>
				)
			}
			if (part.type === "text" && part.content.trim()) {
				return (
					<ReactMarkdown
						key={partId}
						className="prose prose-invert"
						remarkPlugins={[remarkGfm]}
						children={part.content}
						components={{
							a: ({ href, children }) => (
								<LinkButton href={href} children={children} />
							)
						}}
					/>
				)
			}
			return null
		})
	}

	return (
		<div
			className={`p-4 rounded-lg ${
				isUser
					? "bg-[var(--color-accent-blue)] text-white text-base font-medium self-end max-w-[80%] sm:max-w-md lg:max-w-lg"
					: "bg-transparent text-base text-white self-start w-full"
			} mb-2 relative`}
			style={{ wordBreak: "break-word" }}
		>
			{renderMessageContent()}

			{!isUser && (
				<div className="flex justify-start items-center space-x-4 mt-6">
					<Tooltip id="chat-bubble-tooltip" />
					{memoryUsed && (
						<span
							data-tooltip-id="chat-bubble-tooltip"
							data-tooltip-content="Memory was used to generate this response"
							className="flex items-center text-[var(--color-accent-blue)]"
						>
							<IconBrain size={18} />
						</span>
					)}
					{agentsUsed && (
						<span
							data-tooltip-id="chat-bubble-tooltip"
							data-tooltip-content="Agents were used to process this response"
							className="flex items-center text-[var(--color-text-secondary)]"
						>
							<IconSettings size={18} />
						</span>
					)}
					{internetUsed && (
						<span
							data-tooltip-id="chat-bubble-tooltip"
							data-tooltip-content="Internet was used to gather information for this response"
							className="flex items-center text-[var(--color-text-secondary)]"
						>
							<IconGlobe size={18} />
						</span>
					)}
					<button
						onClick={handleCopyToClipboard}
						className="flex items-center text-[var(--color-text-secondary)] hover:text-[var(--color-accent-green)] transition-colors"
						data-tooltip-id="chat-bubble-tooltip"
						data-tooltip-content={
							copied ? "Copied!" : "Copy response"
						}
					>
						{copied ? (
							<IconCheck size={18} />
						) : (
							<IconClipboard size={18} />
						)}
					</button>
				</div>
			)}
		</div>
	)
}

export default ChatBubble
