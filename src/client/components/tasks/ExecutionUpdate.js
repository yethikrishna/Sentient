"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
	IconTool,
	IconBrain,
	IconArrowRight,
	IconMessageCircle,
	IconInfoCircle,
	IconAlertTriangle,
	IconChevronDown
} from "@tabler/icons-react"
import ReactMarkdown from "react-markdown"
import { cn } from "@utils/cn"

const CollapsibleSection = ({
	title,
	icon,
	colorClass,
	children,
	defaultOpen = false
}) => {
	const [isExpanded, setIsExpanded] = useState(defaultOpen)

	return (
		<div
			className={cn(
				"border-l-4 pl-3 mb-2 rounded-md",
				colorClass,
				"bg-neutral-900/60"
			)}
		>
			<button
				className="flex items-center gap-2 w-full text-left focus:outline-none"
				onClick={() => setIsExpanded((prev) => !prev)}
			>
				<span>{icon}</span>
				<span className="font-semibold">{title}</span>
				<IconChevronDown
					size={16}
					className={cn(
						"ml-auto transition-transform",
						isExpanded ? "rotate-180" : ""
					)}
				/>
			</button>
			<AnimatePresence initial={false}>
				{isExpanded && (
					<motion.div
						initial={{ height: 0, opacity: 0 }}
						animate={{ height: "auto", opacity: 1 }}
						exit={{ height: 0, opacity: 0 }}
						transition={{ duration: 0.2 }}
					>
						<div className="mt-2">{children}</div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	)
}

const ExecutionUpdate = ({ update }) => {
	const { message, timestamp } = update

	const formattedTimestamp = new Date(timestamp).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit"
	})

	const { type, content, tool_name, parameters, result, is_error } = message

	const renderContent = () => {
		switch (type) {
			case "info":
				return (
					<div className="flex items-start gap-2 text-neutral-400">
						<IconInfoCircle
							size={16}
							className="flex-shrink-0 mt-0.5 text-neutral-500"
						/>
						<p>{content}</p>
					</div>
				)
			case "error":
				return (
					<div className="flex items-start gap-2 text-red-400">
						<IconAlertTriangle
							size={16}
							className="flex-shrink-0 mt-0.5"
						/>
						<p>{content}</p>
					</div>
				)
			case "thought":
				return (
					<CollapsibleSection
						title="Thought Process"
						icon={
							<IconBrain
								size={16}
								className="text-yellow-400/80"
							/>
						}
						colorClass="border-yellow-500/50"
					>
						<div className="p-3 bg-neutral-800/50 rounded-md">
							<ReactMarkdown className="prose prose-sm prose-invert text-neutral-300 whitespace-pre-wrap break-words">
								{content}
							</ReactMarkdown>
						</div>
					</CollapsibleSection>
				)
			case "tool_call":
				return (
					<CollapsibleSection
						title={`Tool Call: ${tool_name}`}
						icon={<IconTool size={16} className="text-blue-400" />}
						colorClass="border-blue-500/50"
					>
						<div className="p-3 bg-neutral-800/50 rounded-md">
							<pre className="text-xs text-neutral-300 whitespace-pre-wrap font-mono break-all">
								{JSON.stringify(parameters, null, 2)}
							</pre>
						</div>
					</CollapsibleSection>
				)
			case "tool_result":
				return (
					<CollapsibleSection
						title={`Tool Result: ${tool_name}`}
						icon={
							<IconArrowRight
								size={16}
								className={
									is_error ? "text-red-400" : "text-green-400"
								}
							/>
						}
						colorClass={
							is_error
								? "border-red-500/50"
								: "border-green-500/50"
						}
					>
						<div className="p-3 bg-neutral-800/50 rounded-md">
							<pre className="text-xs text-neutral-300 whitespace-pre-wrap font-mono break-all">
								{typeof result === "object"
									? JSON.stringify(result, null, 2)
									: String(result)}
							</pre>
						</div>
					</CollapsibleSection>
				)
			case "final_answer":
				return (
					<div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
						<div className="flex items-center gap-2 font-semibold text-green-300 mb-2">
							<IconMessageCircle size={16} />
							Final Answer
						</div>
						<ReactMarkdown className="prose prose-sm prose-invert text-neutral-200">
							{content}
						</ReactMarkdown>
					</div>
				)
			default:
				return (
					<p className="text-xs font-mono text-neutral-500">
						{JSON.stringify(message)}
					</p>
				)
		}
	}

	return (
		<div className="flex gap-3 text-sm">
			<span className="text-neutral-500 font-mono text-xs flex-shrink-0 pt-1">
				[{formattedTimestamp}]
			</span>
			<div className="flex-1">{renderContent()}</div>
		</div>
	)
}

export default ExecutionUpdate
