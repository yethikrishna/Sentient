"use client"

import React from "react"
import {
	IconTool,
	IconBrain,
	IconArrowRight,
	IconMessageCircle,
	IconInfoCircle,
	IconAlertTriangle
} from "@tabler/icons-react"
import ReactMarkdown from "react-markdown"
import { cn } from "@utils/cn"

const ExecutionUpdate = ({ update }) => {
	const { message, timestamp } = update

	const formattedTimestamp = new Date(timestamp).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit"
	})

	if (typeof message === "string") {
		// Handle old string-based updates for backward compatibility
		return (
			<div className="flex gap-3 text-sm">
				<span className="text-neutral-500 font-mono text-xs flex-shrink-0 pt-0.5">
					[{formattedTimestamp}]
				</span>
				<p className="text-neutral-300">{message}</p>
			</div>
		)
	}

	const { type, content, tool_name, parameters, result, is_error } = message

	const renderContent = () => {
		switch (type) {
			case "info":
				return (
					<div className="flex items-start gap-2 text-neutral-400">
						<IconInfoCircle
							size={16}
							className="flex-shrink-0 mt-1 text-neutral-500"
						/>
						<p>{content}</p>
					</div>
				)
			case "error":
				return (
					<div className="flex items-start gap-2 text-red-400">
						<IconAlertTriangle
							size={16}
							className="flex-shrink-0 mt-1"
						/>
						<p>{content}</p>
					</div>
				)
			case "thought":
				return (
					<div className="flex items-start gap-2 text-neutral-400">
						<IconBrain
							size={16}
							className="flex-shrink-0 mt-1 text-yellow-400/80"
						/>
						<ReactMarkdown className="prose prose-sm prose-invert text-neutral-400">
							{content}
						</ReactMarkdown>
					</div>
				)
			case "tool_call":
				return (
					<div className="flex items-start gap-2">
						<IconTool
							size={16}
							className="flex-shrink-0 mt-1 text-blue-400"
						/>
						<div className="flex-1">
							<p className="font-medium text-neutral-200">
								<span className="text-blue-400">
									Tool Call:
								</span>{" "}
								<span className="font-mono text-sm">
									{tool_name}
								</span>
							</p>
							<pre className="text-xs bg-neutral-900/50 p-2 rounded-md mt-1 whitespace-pre-wrap font-mono border border-neutral-700">
								{JSON.stringify(parameters, null, 2)}
							</pre>
						</div>
					</div>
				)
			case "tool_result":
				return (
					<div className="flex items-start gap-2">
						<IconArrowRight
							size={16}
							className={cn(
								"flex-shrink-0 mt-1",
								is_error ? "text-red-400" : "text-green-400"
							)}
						/>
						<div className="flex-1">
							<p
								className={cn(
									"font-medium",
									is_error ? "text-red-400" : "text-green-400"
								)}
							>
								Tool Result:{" "}
								<span className="font-mono text-sm">
									{tool_name}
								</span>
							</p>
							<pre className="text-xs bg-neutral-900/50 p-2 rounded-md mt-1 whitespace-pre-wrap font-mono border border-neutral-700">
								{typeof result === "object"
									? JSON.stringify(result, null, 2)
									: String(result)}
							</pre>
						</div>
					</div>
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
		<div className="flex gap-3">
			<span className="text-neutral-500 font-mono text-xs flex-shrink-0 pt-1">
				[{formattedTimestamp}]
			</span>
			<div className="flex-1">{renderContent()}</div>
		</div>
	)
}

export default ExecutionUpdate