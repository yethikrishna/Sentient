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

// LinkButton component remains the same...
const LinkButton = ({ href, children }) => {
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
			name: children
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
			name: children
		},
		default: {
			icon: <IconLink size={14} className="mr-1" />,
			name: "Link"
		}
	}

	const getToolDetails = (url) => {
		for (const domain in toolMapping) {
			if (url.includes(domain)) {
				return toolMapping[domain]
			} else if (url.match(/^[^@]+@[\w.-]+\.[a-z]{2,}$/i)) {
				return toolMapping["external-mail"]
			}
		}
		return toolMapping["default"]
	}

	const { icon, name } = getToolDetails(href)

	return (
		<span
			onClick={() => window.open(href, "_blank", "noopener noreferrer")}
			className="bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] hover:border-[var(--color-accent-blue)] py-1 px-2 rounded-md items-center cursor-pointer inline-flex"
			style={{
				display: "inline-flex",
				verticalAlign: "middle"
			}}
		>
			{icon}
			<span>{name}</span>{" "}
		</span>
	)
}

// ToolCodeBlock component remains the same...
const ToolCodeBlock = ({ name, code, isExpanded, onToggle }) => {
	let formattedCode = code
	try {
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

// ToolResultBlock component remains the same...
const ToolResultBlock = ({ name, result, isExpanded, onToggle }) => {
	let formattedResult = result
	try {
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

const ChatBubble = ({
	message,
	isUser,
	memoryUsed,
	agentsUsed,
	internetUsed
}) => {
	const [copied, setCopied] = useState(false)
	const [expandedStates, setExpandedStates] = useState({})

	const handleCopyToClipboard = () => {
		let textToCopy = message
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

	const renderMessageContent = () => {
		if (isUser || typeof message !== "string" || !message) {
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

		// --- START OF THE ROBUST CONTEXTUAL FIX ---

		for (const match of message.matchAll(regex)) {
			// 1. Process the text *before* the current valid tag
			if (match.index > lastIndex) {
				const textContent = message.substring(lastIndex, match.index)
				const lastPart =
					contentParts.length > 0
						? contentParts[contentParts.length - 1]
						: null

				// This is the key: Only add text if it's at the start of the message
				// or if it follows another text block. This filters out any text
				// sandwiched between special tags (e.g., </tool_code>...JUNK...<tool_result>).
				if (!lastPart || lastPart.type === "text") {
					if (textContent.trim()) {
						contentParts.push({
							type: "text",
							content: textContent
						})
					}
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
				contentParts.push({
					type: "tool_code",
					name: subMatch[1],
					code: subMatch[2] ? subMatch[2].trim() : "{}"
				})
			} else if (
				(subMatch = tag.match(
					/<tool_result tool_name="([^"]+)">([\s\S]*?)<\/tool_result>/
				))
			) {
				contentParts.push({
					type: "tool_result",
					name: subMatch[1],
					result: subMatch[2] ? subMatch[2].trim() : "{}"
				})
			} else if ((subMatch = tag.match(/<think>([\s\S]*?)<\/think>/))) {
				const thinkContent = subMatch[1].trim()
				if (thinkContent) {
					contentParts.push({ type: "think", content: thinkContent })
				}
			}

			// 3. Update our position in the message string
			lastIndex = match.index + tag.length
		}

		// 4. Process any remaining text after the last valid tag.
		// This is often the final answer from the assistant.
		if (lastIndex < message.length) {
			const remainingText = message.substring(lastIndex)
			if (remainingText.trim()) {
				contentParts.push({ type: "text", content: remainingText })
			}
		}

		// --- END OF THE ROBUST CONTEXTUAL FIX ---

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