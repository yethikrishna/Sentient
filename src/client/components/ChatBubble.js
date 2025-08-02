import React from "react"
import { useState } from "react"
import { cn } from "@utils/cn"
import {
	IconClipboard,
	IconCheck,
	IconBrain,
	IconLink,
	IconMail,
	IconTrash,
	IconChevronDown,
	IconChevronUp,
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
import FileCard from "./FileCard"

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
	onDelete,
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
		const markdownComponents = {
			a: ({ href, children }) => {
				if (href && href.startsWith("file:")) {
					const filename = href.substring(5)
					return <FileCard filename={filename} />
				}
				return <LinkButton href={href} children={children} />
			}
		}

		if (isUser || typeof contentToRender !== "string" || !contentToRender) {
			return [
				<ReactMarkdown
					key="user-md"
					className="prose prose-invert"
					remarkPlugins={[remarkGfm]}
					children={contentToRender || ""}
					components={markdownComponents}
				/>
			]
		}

		const contentParts = []
		const regex =
			/(<think>[\s\S]*?<\/think>|<tool_(?:code|call)[^>]*>[\s\S]*?<\/tool_code>|<tool_result[^>]*>[\s\S]*?<\/tool_result>|<answer>[\s\S]*?<\/answer>)/g
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
					/<tool_(?:code|call) name="([^"]+)">[\s\S]*?<\/tool_code>/
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
						components={markdownComponents}
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
		// Parse the raw content to extract only the user-facing parts for copying.
		const contentToParse = processedContent.content
		if (!contentToParse || typeof contentToParse !== "string") {
			toast.error("Nothing to copy.")
			return
		}

		const answerParts = []
		const regex =
			/(<think>[\s\S]*?<\/think>|<tool_code[^>]*>[\s\S]*?<\/tool_code>|<tool_result[^>]*>[\s\S]*?<\/tool_result>|<answer>[\s\S]*?<\/answer>)/g
		let lastIndex = 0
		let inToolCallPhase = false // To ignore raw text between tool_code and tool_result

		for (const match of contentToParse.matchAll(regex)) {
			const precedingText = contentToParse.substring(
				lastIndex,
				match.index
			)
			if (precedingText.trim() && !inToolCallPhase) {
				answerParts.push(precedingText.trim())
			}

			const tag = match[0]
			if (tag.startsWith("<tool_code")) inToolCallPhase = true
			else if (tag.startsWith("<tool_result")) inToolCallPhase = false
			else if (tag.startsWith("<answer>")) {
				const answerContent =
					tag.match(/<answer>([\s\S]*?)<\/answer>/)?.[1] || ""
				if (answerContent) answerParts.push(answerContent.trim())
			}
			lastIndex = match.index + tag.length
		}
		const remainingText = contentToParse.substring(lastIndex)
		if (remainingText.trim() && !inToolCallPhase) {
			answerParts.push(remainingText.trim())
		}
		const plainText = answerParts.join("\n\n")

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
			className={cn(
				"max-w-[80%] px-4 py-3 rounded-2xl relative group text-white backdrop-blur-sm",
				isUser
					? "bg-blue-600/30 border border-blue-500/50 rounded-br-none"
					: "bg-neutral-800/30 border border-neutral-700/50 rounded-bl-none"
			)}
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
			<div
				className={cn(
					"absolute top-1/2 -translate-y-1/2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity",
					isUser ? "right-full pr-2" : "left-full pl-2"
				)}
			>
				<button
					onClick={() => onDelete(message.id)}
					className="p-1.5 rounded-full bg-neutral-700 text-neutral-300 hover:bg-red-500/20 hover:text-red-400"
					data-tooltip-id="chat-bubble-tooltip"
					data-tooltip-content="Delete"
				>
					<IconTrash size={16} />
				</button>
				{!isUser && (
					<button
						onClick={() => onReply(message)}
						className="p-1.5 rounded-full bg-neutral-700 text-neutral-300 hover:bg-neutral-600 hover:text-white"
						data-tooltip-id="chat-bubble-tooltip"
						data-tooltip-content="Reply"
					>
						<IconArrowBackUp size={16} />
					</button>
				)}
			</div>
			{!isUser && (
				<div className="flex justify-start items-center mt-4">
					<Tooltip
						place="right-start"
						id="chat-bubble-tooltip"
						style={{ zIndex: 9999 }}
					/>
					<button
						onClick={handleCopyToClipboard}
						className="flex items-center text-neutral-400 hover:text-white transition-colors"
						data-tooltip-id="chat-bubble-tooltip"
						data-tooltip-content={
							copied ? "Copied!" : "Copy response"
						}
					>
						{copied ? (
							<IconCheck size={16} />
						) : (
							<IconClipboard size={16} />
						)}
					</button>
				</div>
			)}
		</div>
	)
}

export default ChatBubble
