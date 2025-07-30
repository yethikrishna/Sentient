import React from "react"
import { useState } from "react"
import {
	IconClipboard,
	IconCheck,
	IconBrain,
	IconSettings,
	IconGlobe,
	IconLink,
	IconMail,
	IconCode,
	IconChevronDown,
	IconChevronUp,
	IconTerminal2,
	IconArrowBackUp
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import IconGoogleDocs from "./icons/IconGoogleDocs"
import IconGoogleSheets from "./icons/IconGoogleSheets"
import IconGoogleCalendar from "./icons/IconGoogleCalendar"
import IconGoogleSlides from "./icons/IconGoogleSlides"
import IconGoogleDrive from "./icons/IconGoogleDrive"
import IconGoogleMail from "./icons/IconGoogleMail"
import toast from "react-hot-toast"

// LinkButton component (no changes needed)
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
			<span>{name}</span>
		</span>
	)
}

// ToolCodeBlock is no longer rendered, but we keep it for potential future use or debugging
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

// ToolResultBlock component to display tool results in a collapsible format
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

// Main ChatBubble component
const ChatBubble = ({
	role,
	content,
	tools = [],
	onReply,
	message,
	allMessages = []
}) => {
	const [copied, setCopied] = useState(false)
	const [expandedStates, setExpandedStates] = useState({})
	const [processedContent, setProcessedContent] = useState({
		content: content,
		repliedTo: null
	})
	const isUser = role === "user"
	const memoryUsed = (tools || []).some(
		(t) => t.includes("memory") || t.includes("history")
	)
	const internetUsed = (tools || []).some(
		(t) => t.includes("search") || t.includes("news")
	)
	const agentsUsed = (tools || []).length > 0

	React.useEffect(() => {
		const replyRegex = /<reply_to id="([^"]+)">[\s\S]*?<\/reply_to>\n*/
		const match = content.match(replyRegex)

		if (match) {
			const repliedToId = match[1]
			const actualContent = content.replace(replyRegex, "")
			const originalMessage = allMessages.find(
				(m) => m.id === repliedToId
			)
			setProcessedContent({
				content: actualContent,
				repliedTo: originalMessage
			})
		} else {
			setProcessedContent({ content: content, repliedTo: null })
		}
	}, [content, allMessages])

	// Function to toggle expansion of collapsible sections
	const toggleExpansion = (id) => {
		setExpandedStates((prev) => ({ ...prev, [id]: !prev[id] }))
	}

	// ***************************************************************
	// *** UPDATED LOGIC: Function to render message content       ***
	// ***************************************************************
	const renderMessageContent = (contentToRender) => {
		if (isUser || typeof contentToRender !== "string" || !contentToRender) {
			return [
				<ReactMarkdown
					key="user-md"
					className="prose prose-invert"
					remarkPlugins={[remarkGfm]}
					children={contentToRender || ""}
					components={{
						a: ({ href, children }) => (
							<LinkButton href={href} children={children} />
						)
					}}
				/>
			]
		}

		const contentParts = []
		const regex =
			/(<think>[\s\S]*?<\/think>|<tool_code[^>]*>[\s\S]*?<\/tool_code>|<tool_result[^>]*>[\s\S]*?<\/tool_result>|<answer>[\s\S]*?<\/answer>)/g
		let lastIndex = 0
		let inToolCallPhase = false

		for (const match of contentToRender.matchAll(regex)) {
			const precedingText = contentToRender.substring(
				lastIndex,
				match.index
			)

			// 1. Add any text that came before the current tag, but only if we're not in the "ignore" phase
			if (precedingText.trim() && !inToolCallPhase) {
				contentParts.push({ type: "answer", content: precedingText })
			}

			// 2. Process the matched tag
			const tag = match[0]
			let subMatch

			if ((subMatch = tag.match(/<think>([\s\S]*?)<\/think>/))) {
				const thinkContent = subMatch[1].trim()
				if (thinkContent) {
					contentParts.push({ type: "think", content: thinkContent })
				}
			} else if (
				(subMatch = tag.match(
					/<tool_code name="([^"]+)">[\s\S]*?<\/tool_code>/
				))
			) {
				// When we find a tool_code, we enter the "ignore" phase and do not render the code itself.
				inToolCallPhase = true
			} else if (
				// CORRECTED REGEX: Added ([\s\S]*?) to capture the result content
				(subMatch = tag.match(
					/<tool_result tool_name="([^"]+)">([\s\S]*?)<\/tool_result>/
				))
			) {
				// When we find a tool_result, we exit the "ignore" phase and render the result.
				inToolCallPhase = false
				contentParts.push({
					type: "tool_result",
					name: subMatch[1],
					result: subMatch[2] ? subMatch[2].trim() : "{}"
				})
			} else if ((subMatch = tag.match(/<answer>([\s\S]*?)<\/answer>/))) {
				const answerContent = subMatch[1]
				if (answerContent) {
					contentParts.push({
						type: "answer",
						content: answerContent
					})
				}
			}
			lastIndex = match.index + tag.length
		}

		// 3. Add any remaining text after the last tag (this is the final, streaming answer)
		const remainingText = contentToRender.substring(lastIndex)
		if (remainingText && !inToolCallPhase) {
			contentParts.push({ type: "answer", content: remainingText })
		}

		// 4. Render all the collected parts into React components
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
			if (part.type === "answer" && part.content) {
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
			// Note: tool_code parts are never rendered
			return null
		})
	}

	const renderedContent = React.useMemo(
		() => renderMessageContent(processedContent.content),
		[processedContent.content, expandedStates, isUser]
	)

	// Function to copy message content to clipboard
	const handleCopyToClipboard = () => {
		// Build the text to copy from the parsed parts, ensuring we only copy the final answer
		const plainText = renderedContent
			.filter((part) => part.type === "answer")
			.map((part) => part.props.children)
			.join("")
			.trim()

		navigator.clipboard
			.writeText(plainText)
			.then(() => {
				setCopied(true)
				setTimeout(() => setCopied(false), 2000)
			})
			.catch((err) => toast.error(`Failed to copy text: ${err}`))
	}

	return (
		<div
			className={`p-4 rounded-lg ${
				isUser ? "bg-[var(--color-accent-blue)]" : "bg-transparent"
			} text-white text-base self-start w-full group relative mb-2`}
			style={{ wordBreak: "break-word" }}
		>
			{processedContent.repliedTo && (
				<div className="mb-3 p-2 border-l-2 border-neutral-500 bg-black/20 rounded-md">
					<p className="text-xs text-neutral-400 font-semibold">
						Replying to{" "}
						{processedContent.repliedTo.role === "user"
							? "you"
							: "assistant"}
					</p>
					<p className="text-sm text-neutral-300 mt-1 truncate">
						{processedContent.repliedTo.content}
					</p>
				</div>
			)}
			{renderedContent}
			<div className="absolute left-0 top-1/2 -translate-x-full -translate-y-1/2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity pr-2">
				<button
					onClick={() => onReply(message)}
					className="p-1.5 rounded-full bg-neutral-700 text-neutral-300 hover:bg-neutral-600 hover:text-white"
					data-tooltip-id="chat-bubble-tooltip"
					data-tooltip-content="Reply"
				>
					<IconArrowBackUp size={16} />
				</button>
			</div>
			{!isUser && (
				<div className="flex justify-start items-center space-x-4 mt-6">
					<Tooltip
						place="right-start"
						id="chat-bubble-tooltip"
						style={{ zIndex: 9999 }}
					/>
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
