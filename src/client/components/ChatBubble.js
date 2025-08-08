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
	IconArrowBackUp,
	IconTool,
	IconFileText,
	IconWorldSearch,
	IconMapPin,
	IconShoppingCart,
	IconChartPie,
	IconBrandTrello,
	IconNews,
	IconListCheck,
	IconBrandDiscord,
	IconBrandWhatsapp,
	IconCalendarEvent,
	IconBrandSlack,
	IconBrandNotion,
	IconBrandGithub,
	IconBrandGoogleDrive,
	IconBrandLinkedin
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import IconGoogleDocs from "./icons/IconGoogleDocs"
import IconGoogleSheets from "./icons/IconGoogleSheets"
import IconGoogleCalendar from "./icons/IconGoogleCalendar"
import IconGoogleSlides from "./icons/IconGoogleSlides" // This is a custom one, not from tabler
import IconGoogleMail from "./icons/IconGoogleMail"
import IconGoogleDrive from "./icons/IconGoogleMail"
import toast from "react-hot-toast"
import FileCard from "./FileCard"

const toolIcons = {
	gmail: IconGoogleMail,
	gdocs: IconFileText,
	gdrive: IconBrandGoogleDrive,
	slack: IconBrandSlack,
	notion: IconBrandNotion,
	github: IconBrandGithub,
	internet_search: IconWorldSearch,
	memory: IconBrain,
	gmaps: IconMapPin,
	linkedin: IconBrandLinkedin,
	gshopping: IconShoppingCart,
	quickchart: IconChartPie,
	google_search: IconWorldSearch,
	trello: IconBrandTrello,
	news: IconNews,
	todoist: IconListCheck,
	discord: IconBrandDiscord,
	whatsapp: IconBrandWhatsapp,
	gcalendar_alt: IconCalendarEvent,
	default: IconTool
}
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
	tools = [], // This is for the icons at the bottom, keep it
	thoughts = [],
	tool_calls = [],
	tool_results = [],
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
		// This effect handles parsing the reply-to block, which is separate
		// from the main content parsing.
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

	// This is the core fix. We parse the content string to extract structured data
	// if it's not already provided as props. This handles both streaming and page-load scenarios.
	const { finalContent, parsedThoughts, parsedToolCalls, parsedToolResults } =
		React.useMemo(() => {
			// If structured data is already provided (from DB on page load), use it directly.
			if (
				(thoughts && thoughts.length > 0) ||
				(tool_calls && tool_calls.length > 0) ||
				(tool_results && tool_results.length > 0)
			) {
				return {
					finalContent: processedContent.content,
					parsedThoughts: thoughts,
					parsedToolCalls: tool_calls,
					parsedToolResults: tool_results
				}
			}

			// Otherwise, parse the raw content string (streaming scenario).
			const localThoughts = []
			const localToolCalls = []
			const localToolResults = []
			const contentString = processedContent.content || ""

			// Extract thoughts
			const thoughtRegex = /<think>([\s\S]*?)<\/think>/g
			let match
			while ((match = thoughtRegex.exec(contentString)) !== null) {
				localThoughts.push(match[1].trim())
			}

			// Extract tool calls
			const toolCallRegex =
				/<tool_code name="([^"]+)">([\s\S]*?)<\/tool_code>/g
			while ((match = toolCallRegex.exec(contentString)) !== null) {
				localToolCalls.push({
					tool_name: match[1],
					parameters: match[2].trim()
				})
			}

			// Extract tool results
			const toolResultRegex =
				/<tool_result tool_name="([^"]+)">([\s\S]*?)<\/tool_result>/g
			while ((match = toolResultRegex.exec(contentString)) !== null) {
				localToolResults.push({
					tool_name: match[1],
					result: match[2].trim()
				})
			}

			// Extract final answer by removing all other tags.
			// The <answer> tag takes precedence.
			const answerMatch = contentString.match(/<answer>([\s\S]*?)<\/answer>/)
			let final
			if (answerMatch) {
				final = answerMatch[1]
			} else {
				final = contentString
					.replace(/<think>[\s\S]*?<\/think>/g, "")
					.replace(/<tool_code[^>]*>[\s\S]*?<\/tool_code>/g, "")
					.replace(/<tool_result[^>]*>[\s\S]*?<\/tool_result>/g, "")
			}

			return {
				finalContent: final.trim(),
				parsedThoughts: localThoughts,
				parsedToolCalls: localToolCalls,
				parsedToolResults: localToolResults
			}
		}, [processedContent.content, thoughts, tool_calls, tool_results])

	// Function to toggle expansion of collapsible sections
	const toggleExpansion = (id) => {
		setExpandedStates((prev) => ({ ...prev, [id]: !prev[id] }))
	}

	// ***************************************************************
	// *** UPDATED LOGIC: Function to render message content       ***
	// ***************************************************************
	const transformLinkUri = (uri) => {
		return uri.startsWith("file:") ? uri : uri // Let ReactMarkdown handle its default security
	}
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

		// User message rendering is simple and unchanged
		if (isUser) {
			return (
				<ReactMarkdown
					className="prose prose-invert"
					remarkPlugins={[remarkGfm]}
					children={contentToRender || ""}
					urlTransform={transformLinkUri}
					components={markdownComponents}
				/>
			)
		}

		// Assistant message rendering now uses the structured props
		return (
			<>
				{parsedThoughts.map((thought, index) => {
					const partId = `thought_${index}`
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
										{thought}
									</ReactMarkdown>
								</div>
							)}
						</div>
					)
				})}

				{parsedToolCalls.map((call, index) => {
					const partId = `tool_call_${index}`
					return (
						<ToolCodeBlock
							key={partId}
							name={call.tool_name}
							code={call.parameters}
							isExpanded={!!expandedStates[partId]}
							onToggle={() => toggleExpansion(partId)}
						/>
					)
				})}

				{parsedToolResults.map((res, index) => {
					const partId = `tool_result_${index}`
					return (
						<ToolResultBlock
							key={partId}
							name={res.tool_name}
							result={res.result}
							isExpanded={!!expandedStates[partId]}
							onToggle={() => toggleExpansion(partId)}
						/>
					)
				})}

				{/* Render the final, clean content */}
				{contentToRender && (
					<div
						className={
							(parsedThoughts.length > 0 ||
								parsedToolCalls.length > 0 ||
								parsedToolResults.length > 0) &&
							"mt-4 pt-4 border-t border-neutral-700/50"
						}
					>
						<ReactMarkdown
							className="prose prose-invert"
							remarkPlugins={[remarkGfm]}
							children={contentToRender}
							urlTransform={transformLinkUri}
							components={markdownComponents}
						/>
					</div>
				)}
			</>
		)
	}

	const renderedContent = React.useMemo(
		() => renderMessageContent(finalContent),
		[
			finalContent,
			expandedStates,
			isUser,
			parsedThoughts,
			parsedToolCalls,
			parsedToolResults
		]
	)

	// Function to copy message content to clipboard
	const handleCopyToClipboard = () => {
		const textToCopy = processedContent.content
		if (!textToCopy) {
			toast.error("Nothing to copy.")
			return
		}
		navigator.clipboard
			.writeText(textToCopy)
			.then(() => {
				setCopied(true)
				setTimeout(() => setCopied(false), 2000)
			})
			.catch((err) => toast.error(`Failed to copy text: ${err}`))
	}

	return (
		<div
			className={cn(
				"px-4 py-3 rounded-2xl relative group text-white backdrop-blur-sm",
				"max-w-full md:max-w-[80%]",
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
			{tools && tools.length > 0 && (
				<div className="flex items-center gap-2 mt-3 text-xs text-neutral-400">
					<IconTool size={14} />
					<div className="flex flex-wrap gap-1.5">
						{tools.map((toolName) => {
							const Icon =
								toolIcons[toolName] || toolIcons.default
							return (
								<div
									key={toolName}
									className="flex items-center gap-1 bg-neutral-800/60 px-2 py-0.5 rounded-full"
								>
									<Icon size={12} />
									<span>{toolName}</span>
								</div>
							)
						})}
					</div>
				</div>
			)}
			<div
				className={cn(
					"flex items-center gap-2 mt-4 transition-opacity",
					"opacity-100 md:opacity-0 group-hover:md:opacity-100",
					isUser ? "justify-end" : "justify-start"
				)}
			>
				<Tooltip
					place={isUser ? "left-start" : "right-start"}
					id="chat-bubble-tooltip"
					style={{ zIndex: 9999 }}
				/>

				{/* Assistant-only buttons */}
				{!isUser && (
					<>
						<button
							onClick={handleCopyToClipboard}
							className="flex items-center p-1.5 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
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
						<button
							onClick={() => onReply(message)}
							className="p-1.5 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
							data-tooltip-id="chat-bubble-tooltip"
							data-tooltip-content="Reply"
						>
							<IconArrowBackUp size={16} />
						</button>
					</>
				)}

				{/* Delete button for both user and assistant */}
				{onDelete && (
					<button
						onClick={() => onDelete(message.id)}
						className="p-1.5 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-red-400"
						data-tooltip-id="chat-bubble-tooltip"
						data-tooltip-content="Delete"
					>
						<IconTrash size={16} />
					</button>
				)}
			</div>
		</div>
	)
}

export default ChatBubble
