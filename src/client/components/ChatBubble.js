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
			onClick={() => window.open(href, "_blank", "noopener noreferrer")} // Open URL in new tab on click
			className="bg-white text-black border-2 border-black hover:border-lightblue py-1 px-2 rounded-md items-center cursor-pointer inline-flex"
			// Styling for the link button: background, text color, border, padding, rounded corners, cursor, inline-flex display
			style={{
				display: "inline-flex", // Ensure inline-flex for proper alignment
				verticalAlign: "middle", // Vertical alignment to middle
				margin: "0 4px" // Margin for spacing between link buttons
			}}
		>
			{icon} {/* Render the icon determined by getToolDetails */}
			<span>{name}</span>{" "}
			{/* Render the name determined by getToolDetails */}
		</span>
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
		if (isUser || typeof message !== "string") {
			// Fallback for user messages or non-string AI messages
			return (
				<ReactMarkdown
					className="prose prose-invert"
					remarkPlugins={[remarkGfm]}
					children={message}
					components={{
						a: ({ href, children }) => (
							<LinkButton href={href} children={children} />
						)
					}}
				/>
			)
		}

		// This is a deprecated way of parsing, new method below is better.
		const contentParts = []
		const regex =
			/(<think>[\s\S]*?<\/think>|<tool_code name="[^"]*">[\s\S]*?<\/tool_code>|<tool_result tool_name="[^"]*">[\s\S]*?<\/tool_result>)/g
		let lastIndex = 0

		for (const match of message.matchAll(regex)) {
			// Capture the text before the current tag
			if (match.index > lastIndex) {
				contentParts.push({
					type: "text",
					content: message.substring(lastIndex, match.index)
				})
			}

			// Parse the tag itself
			const tag = match[0]
			let subMatch
			if ((subMatch = tag.match(/<think>([\s\S]*?)<\/think>/))) {
				contentParts.push({
					type: "think",
					content: subMatch[1].trim()
				})
			} else if (
				(subMatch = tag.match(
					/<tool_code name="([^"]*)">([\s\S]*?)<\/tool_code>/
				))
			) {
				contentParts.push({
					type: "tool_code",
					name: subMatch[1],
					content: subMatch[2].trim()
				})
			} else if (
				(subMatch = tag.match(
					/<tool_result tool_name="([^"]*)">([\s\S]*?)<\/tool_result>/
				))
			) {
				contentParts.push({
					type: "tool_result",
					name: subMatch[1],
					content: subMatch[2].trim()
				})
			}
			lastIndex = match.index + tag.length
		}

		// Capture any remaining text after the last tag
		if (lastIndex < message.length) {
			contentParts.push({
				type: "text",
				content: message.substring(lastIndex)
			})
		}

		return contentParts.map((part, index) => {
			const partId = `${part.type}_${index}`
			if (part.type === "think") {
				return (
					<div
						key={partId}
						className="mb-4 border-l-2 border-yellow-500 pl-3"
					>
						<button
							onClick={() => toggleExpansion(partId)}
							className="flex items-center gap-2 text-yellow-400 hover:text-yellow-300 text-sm font-semibold"
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
					<div
						key={partId}
						className="mb-4 border-l-2 border-cyan-500 pl-3"
					>
						<button
							onClick={() => toggleExpansion(partId)}
							className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 text-sm font-semibold"
						>
							{expandedStates[partId] ? (
								<IconChevronUp size={16} />
							) : (
								<IconChevronDown size={16} />
							)}
							<IconCode size={16} />
							Tool Call: {part.name}
						</button>
						{expandedStates[partId] && (
							<div className="mt-2 p-3 bg-neutral-800/50 rounded-md">
								<pre className="text-xs text-gray-300 whitespace-pre-wrap bg-transparent p-0 m-0 font-mono">
									<code>
										{(() => {
											try {
												return JSON.stringify(
													JSON.parse(part.content),
													null,
													2
												)
											} catch (e) {
												return part.content // Fallback to raw string if not valid JSON
											}
										})()}
									</code>
								</pre>
							</div>
						)}
					</div>
				)
			}
			if (part.type === "tool_result") {
				return (
					<div
						key={partId}
						className="mb-4 border-l-2 border-lime-500 pl-3"
					>
						<button
							onClick={() => toggleExpansion(partId)}
							className="flex items-center gap-2 text-lime-400 hover:text-lime-300 text-sm font-semibold"
						>
							{expandedStates[partId] ? (
								<IconChevronUp size={16} />
							) : (
								<IconChevronDown size={16} />
							)}
							<IconTerminal2 size={16} />
							Tool Result: {part.name}
						</button>
						{expandedStates[partId] && (
							<div className="mt-2 p-3 bg-neutral-800/50 rounded-md">
								<pre className="text-xs text-gray-300 whitespace-pre-wrap bg-transparent p-0 m-0 font-mono">
									<code>{part.content}</code>
								</pre>
							</div>
						)}
					</div>
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
					? "bg-white text-black text-lg font-semibold self-end max-w-xs md:max-w-md lg:max-w-lg mt-5 mb-5"
					: "bg-transparent text-lg text-white self-start w-full border-b border-t border-lightblue"
			} mb-2 relative font-Inter`}
			style={{ wordBreak: "break-word" }}
		>
			{renderMessageContent()}

			{!isUser && (
				<div className="flex justify-start items-center space-x-4 mt-6">
					{memoryUsed && (
						<>
							<span
								data-tooltip-id="memory-used"
								data-tooltip-content="Memory was used to generate this response"
								className="flex items-center text-gray-400"
							>
								<IconBrain size={18} />
							</span>
							<Tooltip
								id="memory-used"
								place="right"
								type="dark"
								effect="float"
							/>
						</>
					)}
					{agentsUsed && (
						<>
							<span
								data-tooltip-id="agents-used"
								data-tooltip-content="Agents were used to process this response"
								className="flex items-center text-gray-400"
							>
								<IconSettings size={18} />
							</span>
							<Tooltip
								id="agents-used"
								place="right"
								type="dark"
								effect="float"
							/>
						</>
					)}
					{internetUsed && (
						<>
							<span
								data-tooltip-id="internet-used"
								data-tooltip-content="Internet was used to gather information for this response"
								className="flex items-center text-gray-400"
							>
								<IconGlobe size={18} />
							</span>
							<Tooltip
								id="internet-used"
								place="right"
								type="dark"
								effect="float"
							/>
						</>
					)}
					<button
						onClick={handleCopyToClipboard}
						className="flex items-center text-gray-400 hover:text-green-500 transition-colors"
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
