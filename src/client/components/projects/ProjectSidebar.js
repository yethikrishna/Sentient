"use client"

import React from "react"
import Link from "next/link"
import {
	IconMessage,
	IconChecklist,
	IconPlus,
	IconSettings
} from "@tabler/icons-react"
import { cn } from "@utils/cn"

const ProjectSidebar = ({
	project,
	activeView,
	onViewChange,
	activeChatId,
	onChatSelect,
	onNewChat
}) => {
	const chats = project?.chats || []

	return (
		<div className="bg-neutral-900/50 flex flex-col h-full w-72 border-r border-neutral-800 shrink-0">
			<div className="p-4 border-b border-neutral-800">
				<h2 className="font-semibold text-white text-lg truncate">
					{project?.name}
				</h2>
				<p className="text-xs text-neutral-400">Project Workspace</p>
			</div>

			{/* Main Navigation */}
			<div className="p-2">
				<button
					onClick={() => onViewChange("tasks")}
					className={cn(
						"w-full flex items-center gap-3 p-2.5 rounded-lg text-sm font-medium transition-colors",
						activeView === "tasks"
							? "bg-blue-600/20 text-blue-300"
							: "text-neutral-300 hover:bg-neutral-700/50"
					)}
				>
					<IconChecklist size={18} />
					Tasks
				</button>
			</div>

			{/* Chat History */}
			<div className="flex-1 flex flex-col overflow-hidden">
				<div className="flex items-center justify-between p-4 border-t border-neutral-800">
					<h3 className="font-semibold text-white text-base">
						Conversations
					</h3>
					<button
						onClick={onNewChat}
						className="p-1.5 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded-md"
					>
						<IconPlus size={16} />
					</button>
				</div>
				<div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1.5">
					{chats.map((chat) => (
						<button
							key={chat.chat_id}
							onClick={() => onChatSelect(chat.chat_id)}
							className={cn(
								"w-full text-left p-2.5 rounded-lg transition-colors text-sm flex items-center gap-3",
								activeView === "chat" &&
									activeChatId === chat.chat_id
									? "bg-blue-600 text-white"
									: "text-neutral-300 hover:bg-neutral-700/50"
							)}
						>
							<IconMessage size={18} className="flex-shrink-0" />
							<span className="truncate flex-1">
								{chat.title}
							</span>
						</button>
					))}
					{chats.length === 0 && (
						<p className="text-center text-xs text-neutral-500 p-4">
							No conversations yet. Start one!
						</p>
					)}
				</div>
			</div>
		</div>
	)
}

export default ProjectSidebar
