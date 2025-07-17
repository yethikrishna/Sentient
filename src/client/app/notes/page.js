"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import toast from "react-hot-toast"
import { motion, AnimatePresence } from "framer-motion"
import {
	IconPencil,
	IconLoader,
	IconPlus,
	IconTrash,
	IconGripVertical,
	IconLink,
	IconNote,
	IconBold,
	IconItalic,
	IconUnderline,
	IconList,
	IconListNumbers,
	IconH1,
	IconH2,
	IconH3,
	IconBlockquote
} from "@tabler/icons-react"
import { useRouter } from "next/navigation"
import { format, formatDistanceToNow } from "date-fns"
import { cn } from "@utils/cn"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

const MarkdownToolbar = ({ textareaRef }) => {
	const applyFormat = (prefix, suffix = "") => {
		const textarea = textareaRef.current
		if (!textarea) return

		const start = textarea.selectionStart
		const end = textarea.selectionEnd
		const selectedText = textarea.value.substring(start, end)
		const newText = `${prefix}${selectedText}${suffix}`

		document.execCommand("insertText", false, newText)
	}

	const applyList = (prefix) => {
		const textarea = textareaRef.current
		if (!textarea) return

		const start = textarea.selectionStart
		const value = textarea.value

		// Find the start of the current line
		let lineStart = start
		while (lineStart > 0 && value[lineStart - 1] !== "\n") {
			lineStart--
		}

		const newText = `${prefix} `
		document.execCommand("insertText", false, newText)
	}

	return (
		<div className="flex items-center gap-2 p-2 bg-neutral-800 rounded-t-lg border-b border-neutral-700">
			<button
				onClick={() => applyFormat("**", "**")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconBold size={16} />
			</button>
			<button
				onClick={() => applyFormat("*", "*")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconItalic size={16} />
			</button>
			<div className="w-px h-5 bg-neutral-700" />
			<button
				onClick={() => applyFormat("# ")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconH1 size={16} />
			</button>
			<button
				onClick={() => applyFormat("## ")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconH2 size={16} />
			</button>
			<button
				onClick={() => applyFormat("### ")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconH3 size={16} />
			</button>
			<div className="w-px h-5 bg-neutral-700" />
			<button
				onClick={() => applyList("-")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconList size={16} />
			</button>
			<button
				onClick={() => applyList("1.")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconListNumbers size={16} />
			</button>
			<button
				onClick={() => applyFormat("> ")}
				className="p-1.5 hover:bg-neutral-700 rounded-md"
			>
				<IconBlockquote size={16} />
			</button>
		</div>
	)
}

const NotesPage = () => {
	const [notes, setNotes] = useState([])
	const [selectedNote, setSelectedNote] = useState(null)
	const [currentDate, setCurrentDate] = useState(format(new Date(), "yyyy-MM-dd"))
	const [isLoading, setIsLoading] = useState(true)
	const [isSaving, setIsSaving] = useState(false)
	const [editorTitle, setEditorTitle] = useState("")
	const [editorContent, setEditorContent] = useState("")
	const textareaRef = useRef(null)
	const router = useRouter()

	const fetchNotes = useCallback(async () => {
		setIsLoading(true)
		try {
			const response = await fetch(`/api/notes?date=${currentDate}`)
			if (!response.ok) throw new Error("Failed to fetch notes")
			const data = await response.json()
			setNotes(
				data.notes.sort(
					(a, b) => new Date(b.updated_at) - new Date(a.updated_at)
				)
			)
			// If a note was selected, and we change date, it should be deselected.
			setSelectedNote(null)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

    useEffect(() => {
        fetchNotes()
    }, [currentDate, fetchNotes])

	useEffect(() => {
		if (selectedNote) {
			setEditorTitle(selectedNote.title)
			setEditorContent(selectedNote.content)
		} else {
			setEditorTitle("")
			setEditorContent("")
		}
	}, [selectedNote])

	const handleSelectNote = (note) => {
		if (isSaving) {
			toast.error("Please wait until the current note is saved.")
			return
		}
		setSelectedNote(note)
	}

	const handleNewNote = () => {
		if (isSaving) {
			toast.error("Please wait until the current note is saved.")
			return
		}
		setSelectedNote(null)
		setEditorTitle("New Note")
		setEditorContent("")
	}

	const handleSaveNote = async () => {
		if (!editorTitle.trim()) {
			toast.error("Note title cannot be empty.")
			return
		}
		setIsSaving(true)

		const payload = {
			title: editorTitle,
			content: editorContent,
			note_date: currentDate
		}

		try {
			let response
			let data
			if (selectedNote) {
				// Update existing note
				response = await fetch(`/api/notes/${selectedNote.note_id}`, {
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload)
				})
				if (!response.ok) throw new Error("Failed to update note")
				data = await response.json()
				// Update note in local state
				setNotes(
					notes.map((n) =>
						n.note_id === data.note.note_id ? data.note : n
					)
				)
				toast.success("Note updated!")
			} else {
				// Create new note
				response = await fetch("/api/notes", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload)
				})
				if (!response.ok) throw new Error("Failed to create note")
				data = await response.json()
				// Add new note to local state and select it
				const newNote = data.note
				setNotes([newNote, ...notes])
				setSelectedNote(newNote)
				toast.success("Note created and sent for processing!")
			}
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSaving(false)
		}
	}

	const handleDeleteNote = async (noteId) => {
		if (!window.confirm("Are you sure you want to delete this note?"))
			return

		try {
			const response = await fetch(`/api/notes/${noteId}`, {
				method: "DELETE"
			})
			if (!response.ok) throw new Error("Failed to delete note")

			setNotes(notes.filter((n) => n.note_id !== noteId))
			if (selectedNote && selectedNote.note_id === noteId) {
				setSelectedNote(null)
			}
			toast.success("Note deleted.")
		} catch (error) {
			toast.error(error.message)
		}
	}

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)] text-white overflow-hidden pl-0 md:pl-20">
			{/* Notes List Panel */}
			<div className="w-1/3 max-w-sm border-r border-neutral-800 flex flex-col">
				<div className="p-3 border-b border-neutral-800 flex justify-between items-center gap-2">
					<input
						type="date"
						value={currentDate}
						onChange={e => setCurrentDate(e.target.value)}
						className="p-2 bg-neutral-800 rounded-lg text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
					<button
						onClick={handleNewNote}
						className="p-2 hover:bg-neutral-700 rounded-lg"
					>
						<IconPlus size={20} />
					</button>
				</div>
				<div className="flex-1 overflow-y-auto custom-scrollbar">
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="animate-spin" />
						</div>
					) : (
						notes.map((note) => (
							<div
								key={note.note_id}
								onClick={() => handleSelectNote(note)}
								className={cn(
									"p-4 border-b border-neutral-800 cursor-pointer hover:bg-neutral-800/50",
									selectedNote?.note_id === note.note_id &&
										"bg-[var(--color-primary-surface)]"
								)}
							>
								<h3 className="font-semibold truncate">
									{note.title}
								</h3>
								<p className="text-sm text-neutral-400 mt-1 line-clamp-2">
									{note.content || "No content"}
								</p>
								<div className="flex justify-between items-center mt-2">
									<p className="text-xs text-neutral-500">
										{formatDistanceToNow(
											new Date(note.updated_at),
											{ addSuffix: true }
										)}
									</p>
									<div className="flex items-center gap-2">
										{note.linked_task_ids &&
											note.linked_task_ids.length > 0 && (
												<IconLink
													size={14}
													className="text-blue-400"
												/>
											)}
										<button
											onClick={(e) => {
												e.stopPropagation()
												handleDeleteNote(note.note_id)
											}}
											className="p-1 text-neutral-500 hover:text-red-500"
										>
											<IconTrash size={14} />
										</button>
									</div>
								</div>
							</div>
						))
					)}
				</div>
			</div>

			{/* Editor Panel */}
			<div className="flex-1 flex flex-col">
				<AnimatePresence>
					{selectedNote === null && !editorTitle ? (
						<div className="flex-1 flex flex-col justify-center items-center text-neutral-500">
							<IconNote size={48} />
							<p className="mt-4">
								Select a note or create a new one.
							</p>
						</div>
					) : (
						<motion.div
							initial={{ opacity: 0 }}
							animate={{ opacity: 1 }}
							className="flex-1 flex flex-col"
						>
							<div className="p-4 border-b border-neutral-800">
								<input
									type="text"
									value={editorTitle}
									onChange={(e) =>
										setEditorTitle(e.target.value)
									}
									placeholder="Note Title"
									className="w-full bg-transparent text-xl font-semibold focus:outline-none"
								/>
							</div>
							<div className="flex-1 flex flex-col overflow-hidden">
								<MarkdownToolbar textareaRef={textareaRef} />
								<textarea
									ref={textareaRef}
									value={editorContent}
									onChange={(e) =>
										setEditorContent(e.target.value)
									}
									placeholder="Start writing your note here..."
									className="w-full h-full p-4 bg-neutral-900 focus:outline-none resize-none custom-scrollbar"
								/>
							</div>
							<div className="p-4 border-t border-neutral-800 flex justify-end">
								<button
									onClick={handleSaveNote}
									disabled={isSaving}
									className="bg-blue-600 hover:bg-blue-500 px-5 py-2 rounded-lg font-semibold flex items-center gap-2 disabled:opacity-50"
								>
									{isSaving ? (
										<IconLoader className="animate-spin" />
									) : (
										<IconPencil />
									)}
									{isSaving ? "Saving..." : "Save Note"}
								</button>
							</div>
						</motion.div>
					)}
				</AnimatePresence>
			</div>
		</div>
	)
}

export default NotesPage
