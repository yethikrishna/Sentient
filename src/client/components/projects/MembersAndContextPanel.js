"use client"

import React, { useState } from "react"
import { useUser } from "@auth0/nextjs-auth0"
import {
	IconUsers,
	IconFileText,
	IconPlus,
	IconTrash,
	IconLoader
} from "@tabler/icons-react"
import toast from "react-hot-toast"

const MembersAndContextPanel = ({ project, onDataChange }) => {
	const { user: currentUser } = useUser()
	const [newMemberId, setNewMemberId] = useState("")
	const [newContextText, setNewContextText] = useState("")
	const [isInviting, setIsInviting] = useState(false)
	const [isAddingContext, setIsAddingContext] = useState(false)

	const isOwner = currentUser?.sub === project?.owner_id

	const handleInviteMember = async () => {
		if (!newMemberId.trim()) return
		setIsInviting(true)
		try {
			const res = await fetch(
				`/api/projects/${project.project_id}/members`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ user_id: newMemberId.trim() })
				}
			)
			if (!res.ok) throw new Error("Failed to invite member")
			toast.success("Member invited!")
			setNewMemberId("")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsInviting(false)
		}
	}

	const handleRemoveMember = async (memberId) => {
		if (!window.confirm("Are you sure you want to remove this member?"))
			return
		try {
			const res = await fetch(
				`/api/projects/${project.project_id}/members/${memberId}`,
				{
					method: "DELETE"
				}
			)
			if (!res.ok) throw new Error("Failed to remove member")
			toast.success("Member removed.")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		}
	}

	const handleAddContext = async () => {
		if (!newContextText.trim()) return
		setIsAddingContext(true)
		try {
			const res = await fetch(
				`/api/projects/${project.project_id}/context`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						type: "text",
						content: newContextText.trim()
					})
				}
			)
			if (!res.ok) throw new Error("Failed to add context")
			toast.success("Context added.")
			setNewContextText("")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsAddingContext(false)
		}
	}

	return (
		<div className="w-80 bg-neutral-950/50 border-l border-neutral-800 shrink-0 p-4 flex flex-col h-full">
			{/* Members Section */}
			<div className="mb-6">
				<h3 className="font-semibold text-white flex items-center gap-2 mb-3">
					<IconUsers size={18} /> Members
				</h3>
				<div className="space-y-2">
					{project?.members?.map((member) => (
						<div
							key={member.user_id}
							className="flex items-center justify-between text-sm text-neutral-300 bg-neutral-800/50 p-2 rounded-md group"
						>
							<div className="flex items-center gap-2">
								<img
									src={`https://i.pravatar.cc/150?u=${member.user_id}`}
									alt="avatar"
									className="w-6 h-6 rounded-full"
								/>
								<span className="truncate">
									{member.user_id.split("|")[1] ||
										member.user_id}
								</span>
								{member.role === "owner" && (
									<span className="text-xs text-yellow-400">
										(Owner)
									</span>
								)}
							</div>
							{isOwner && member.user_id !== currentUser.sub && (
								<button
									onClick={() =>
										handleRemoveMember(member.user_id)
									}
									className="opacity-0 group-hover:opacity-100 text-red-400"
								>
									<IconTrash size={14} />
								</button>
							)}
						</div>
					))}
				</div>
				{isOwner && (
					<div className="mt-3 flex gap-2">
						<input
							type="text"
							value={newMemberId}
							onChange={(e) => setNewMemberId(e.target.value)}
							placeholder="Enter User ID to invite..."
							className="flex-grow p-2 bg-neutral-800 border border-neutral-700 rounded-md text-xs"
						/>
						<button
							onClick={handleInviteMember}
							disabled={isInviting}
							className="p-2 bg-blue-600 rounded-md disabled:opacity-50"
						>
							{isInviting ? (
								<IconLoader
									size={16}
									className="animate-spin"
								/>
							) : (
								<IconPlus size={16} />
							)}
						</button>
					</div>
				)}
			</div>

			{/* Context Section */}
			<div className="flex-1 flex flex-col overflow-hidden">
				<h3 className="font-semibold text-white flex items-center gap-2 mb-3">
					<IconFileText size={18} /> Shared Context
				</h3>
				<div className="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-1">
					{project?.context_items?.map((item) => (
						<div
							key={item.item_id}
							className="text-xs text-neutral-400 bg-neutral-800/50 p-2 rounded-md"
						>
							<p className="font-medium text-neutral-200 truncate">
								{item.type === "text"
									? "Text Snippet"
									: "Google Drive File"}
							</p>
							<p className="truncate">
								{typeof item.content === "string"
									? item.content
									: item.content.file_name}
							</p>
						</div>
					))}
				</div>
				<div className="mt-3 flex gap-2 pt-3 border-t border-neutral-800">
					<textarea
						value={newContextText}
						onChange={(e) => setNewContextText(e.target.value)}
						placeholder="Add a text snippet..."
						rows={2}
						className="flex-grow p-2 bg-neutral-800 border border-neutral-700 rounded-md text-xs resize-none"
					/>
					<button
						onClick={handleAddContext}
						disabled={isAddingContext}
						className="p-2 bg-blue-600 rounded-md self-start disabled:opacity-50"
					>
						{isAddingContext ? (
							<IconLoader size={16} className="animate-spin" />
						) : (
							<IconPlus size={16} />
						)}
					</button>
				</div>
			</div>
		</div>
	)
}

export default MembersAndContextPanel
