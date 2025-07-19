"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import toast from "react-hot-toast"
import { motion, AnimatePresence, Reorder } from "framer-motion"
import {
	IconLoader,
	IconPlus,
	IconTrash,
	IconNote,
	IconSearch,
	IconTag,
	IconPencil,
	IconHelpCircle,
	IconDots,
	IconCalendar,
	IconUserCircle,
	IconPaperclip,
	IconX
} from "@tabler/icons-react"
import {
	IconNote as IconTaskNote, // Alias to avoid conflict
	IconChevronRight
} from "@tabler/icons-react"
import { useEditor, EditorContent, BubbleMenu } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import {
	format,
	isToday,
	isYesterday,
	differenceInDays,
	parseISO
} from "date-fns"
import { cn } from "@utils/cn"
import Editor from "@components/notes/Editor"
import { useSearchParams, useRouter } from "next/navigation"
import { Tooltip } from "react-tooltip" // eslint-disable-line
import ModalDialog from "@components/ModalDialog"
import { taskStatusColors } from "@components/tasks/constants"

const useDebounce = (value, delay) => {
	const [debouncedValue, setDebouncedValue] = useState(value)

	useEffect(() => {
		const handler = setTimeout(() => setDebouncedValue(value), delay)
		return () => clearTimeout(handler)
	}, [value, delay])
	return debouncedValue
}

const HelpTooltip = ({ content }) => (
	<div className="fixed bottom-6 left-6 z-40">
		<button
			data-tooltip-id="page-help-tooltip"
			data-tooltip-content={content}
			className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
		>
			<IconHelpCircle size={22} />
		</button>
	</div>
)

const GeneratedTaskCard = ({ task, onClick }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const schedule = task.schedule?.run_at
		? new Date(task.schedule.run_at).toLocaleDateString()
		: "Unscheduled"

	return (
		<motion.div
			onClick={() => onClick(task.task_id)}
			className="flex items-center justify-between p-3 rounded-lg bg-neutral-800/50 hover:bg-neutral-700/50 cursor-pointer transition-colors"
			whileHover={{ x: 5 }}
		>
			<div className="flex items-center gap-3 min-w-0">
				<statusInfo.icon
					className={cn("h-5 w-5 flex-shrink-0", statusInfo.color)}
				/>
				<div className="min-w-0">
					<p className="text-sm text-white truncate">
						{task.description}
					</p>
					<p className="text-xs text-neutral-400">
						{statusInfo.label} • {schedule}
					</p>
				</div>
			</div>
			<IconChevronRight
				size={18}
				className="text-neutral-500 flex-shrink-0"
			/>
		</motion.div>
	)
}

const GeneratedTasksSection = ({ tasks, onTaskClick }) => (
	<div className="flex-shrink-0 border-t border-neutral-700 p-4 bg-slate-950/20">
		<h3 className="text-md font-semibold text-neutral-300 mb-3">
			Generated Tasks
		</h3>
		<div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
			{tasks.map((task) => (
				<GeneratedTaskCard
					key={task.task_id}
					task={task}
					onClick={onTaskClick}
				/>
			))}
		</div>
	</div>
)

const NotesPage = () => {
	const [allNotes, setAllNotes] = useState([])
	const [selectedNote, setSelectedNote] = useState(null)
	const [fullSelectedNote, setFullSelectedNote] = useState(null)
	const [isLoading, setIsLoading] = useState(true)
	const [saveStatus, setSaveStatus] = useState("Saved")
	const [searchQuery, setSearchQuery] = useState("")
	const [deletingNote, setDeletingNote] = useState(null)

	const searchParams = useSearchParams()
	const router = useRouter()

	const [editorContent, setEditorContent] = useState("")
	const [editorTitle, setEditorTitle] = useState("")

	const debouncedContent = useDebounce(editorContent, 1500)
	const debouncedTitle = useDebounce(editorTitle, 1500)

	const fetchNotes = useCallback(async (query = "") => {
		setIsLoading(true)
		const url = query
			? `/api/notes?q=${encodeURIComponent(query)}`
			: "/api/notes"
		try {
			const response = await fetch(url)
			if (!response.ok) throw new Error("Failed to fetch notes")
			const data = await response.json()
			setAllNotes(
				data.notes.sort(
					(a, b) => new Date(b.updated_at) - new Date(a.updated_at)
				)
			)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchNotes()
	}, [fetchNotes])

	// Effect to fetch full note details (including linked tasks) when a note is selected
	useEffect(() => {
		if (selectedNote && !selectedNote.isNew) {
			setFullSelectedNote(null) // Clear old data
			fetch(`/api/notes/${selectedNote.note_id}`)
				.then((res) => res.json())
				.then((data) => {
					setFullSelectedNote(data)
				})
				.catch((err) =>
					console.error("Failed to fetch full note details", err)
				)
		} else {
			setFullSelectedNote(selectedNote)
		}
	}, [selectedNote])

	useEffect(() => {
		if (selectedNote) {
			setEditorTitle(selectedNote.title)
			setEditorContent(selectedNote.content)
			setSaveStatus("Saved")
		} else {
			setEditorTitle("")
			setEditorContent("")
		}
	}, [selectedNote])

	const handleSaveNote = useCallback(async () => {
		if (!selectedNote || saveStatus !== "Unsaved") return

		setSaveStatus("Saving...")

		const isNewNote = selectedNote.isNew
		const payload = {
			title: editorTitle,
			content: editorContent,
			note_date: selectedNote.note_date,
			tags: selectedNote.tags || []
		}
		const url = isNewNote
			? "/api/notes"
			: `/api/notes/${selectedNote.note_id}`
		const method = isNewNote ? "POST" : "PUT"

		try {
			const response = await fetch(url, {
				method,
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload)
			})
			if (!response.ok) throw new Error("Failed to save note")
			const data = await response.json()
			setAllNotes((prev) =>
				(isNewNote
					? [
							data.note,
							...prev.filter(
								(n) => n.note_id !== selectedNote.note_id
							)
						]
					: prev.map((n) =>
							n.note_id === data.note.note_id ? data.note : n
						)
				).sort(
					(a, b) => new Date(b.updated_at) - new Date(a.updated_at)
				)
			)

			setSelectedNote((prev) =>
				isNewNote
					? { ...data.note, isNew: false }
					: { ...prev, ...data.note }
			)
			setSaveStatus("Saved")
		} catch (error) {
			toast.error(error.message)
			setSaveStatus("Unsaved")
		}
	}, [editorContent, editorTitle, saveStatus, selectedNote])

	useEffect(() => {
		if (saveStatus === "Unsaved") void handleSaveNote()
	}, [debouncedContent, debouncedTitle, handleSaveNote, saveStatus])

	const handleNewNote = useCallback(() => {
		if (saveStatus === "Saving...") {
			toast.error("Please wait.")
			return
		}
		const newNote = {
			note_id: `new-note-${Date.now()}`,
			title: "Untitled Note",
			content: "",
			tags: [],
			note_date: new Date().toISOString().split("T")[0],
			updated_at: new Date().toISOString(),
			isNew: true
		}
		setSelectedNote(newNote)
		setSaveStatus("Unsaved")
	}, [saveStatus])

	useEffect(() => {
		if (searchParams.get("action") === "new") {
			handleNewNote()
			router.replace("/notes", { scroll: false }) // Remove query param
		}
	}, [searchParams, handleNewNote, router])

	const handleDeleteNote = async (noteId) => {
		const isNewUnsavedNote = allNotes.find(
			(n) => n.note_id === noteId && n.isNew
		)
		setAllNotes((prev) => prev.filter((n) => n.note_id !== noteId))
		if (selectedNote?.note_id === noteId) setSelectedNote(null)
		if (isNewUnsavedNote) return // No API call needed for unsaved new notes

		try {
			const response = await fetch(`/api/notes/${noteId}`, {
				method: "DELETE"
			})
			if (!response.ok) throw new Error("Failed to delete note")
			toast.success("Note deleted.")
		} catch (error) {
			toast.error(`Delete failed: ${error.message}`)
			fetchNotes() // Re-fetch to restore note if deletion failed
		}
		setDeletingNote(null)
	}

	const filteredNotes = useMemo(() => {
		return searchQuery
			? allNotes.filter(
					(n) =>
						n.title
							.toLowerCase()
							.includes(searchQuery.toLowerCase()) ||
						n.content
							.toLowerCase()
							.includes(searchQuery.toLowerCase())
				)
			: allNotes
	}, [allNotes, searchQuery])

	const recentNotes = useMemo(() => {
		const groups = {
			Today: [],
			Yesterday: [],
			"Previous 7 Days": [],
			Older: []
		}

		filteredNotes.forEach((note) => {
			const date = parseISO(note.updated_at)
			if (isToday(date)) groups.Today.push(note)
			else if (isYesterday(date)) groups.Yesterday.push(note)
			else if (differenceInDays(new Date(), date) < 7)
				groups["Previous 7 Days"].push(note)
			else groups.Older.push(note)
		})
		return Object.entries(groups).filter(([_, notes]) => notes.length > 0)
	}, [filteredNotes])

	const NoteCard = ({ note, onSelect, onDelete, isSelected }) => (
		<Reorder.Item
			value={note}
			id={note.note_id}
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, scale: 0.9 }}
			transition={{ duration: 0.2 }}
			whileHover={{ y: -5 }}
			onClick={() => onSelect(note)}
			className={cn(
				"bg-gradient-to-br from-[var(--color-primary-surface)] to-neutral-900/50",
				"rounded-2xl p-5 flex flex-col cursor-pointer border",
				"border-[var(--color-primary-surface-elevated)] hover:border-[var(--color-accent-blue)]/50 transition-all duration-300 shadow-lg"
			)}
			style={{ breakInside: "avoid-column" }}
		>
			<div className="flex justify-between items-start mb-3">
				<div className="flex flex-wrap gap-1.5">
					{(note.tags || []).map((tag, i) => (
						<span
							key={i}
							className="text-xs font-semibold px-2.5 py-1 bg-[var(--color-accent-purple)]/20 text-[var(--color-accent-purple)] rounded-full"
						>
							{tag}
						</span>
					))}
				</div>
				<div className="relative group/menu">
					<button
						onClick={(e) => {
							e.stopPropagation()
							onDelete(note)
						}}
						className="p-1 text-neutral-500 hover:text-white"
					>
						<IconDots />
					</button>
				</div>
			</div>

			<h3 className="text-lg font-semibold text-white mb-2">
				{note.title || "Untitled Note"}
			</h3>
			<div
				className="text-sm text-[var(--color-text-secondary)] line-clamp-4 flex-grow mb-4"
				dangerouslySetInnerHTML={{
					__html:
						note.content
							.replace(/<[^>]+>/g, " ")
							.substring(0, 200) + "..."
				}}
			/>

			<div className="flex justify-between items-center mt-auto pt-3 border-t border-neutral-700/50">
				<div className="flex items-center gap-2">
					<div className="flex -space-x-2">
						<IconUserCircle className="h-6 w-6 text-neutral-500" />
					</div>
					<IconPaperclip size={16} className="text-neutral-500" />
					<span className="text-xs text-neutral-500">1</span>
				</div>
				<div className="flex items-center gap-2 text-xs text-neutral-500">
					<IconCalendar size={14} />
					<span>
						{format(parseISO(note.updated_at), "MMM d, yyyy")}
					</span>
				</div>
			</div>
		</Reorder.Item>
	)

	const AddNoteCard = () => (
		<button
			onClick={handleNewNote}
			className="bg-transparent rounded-2xl p-5 flex flex-col items-center justify-center border-2 border-dashed border-neutral-700 hover:border-[var(--color-accent-blue)] hover:text-[var(--color-accent-blue)] transition-all duration-300 text-neutral-600 min-h-[180px]"
			style={{ breakInside: "avoid-column" }}
		>
			<IconPlus size={32} />
			<span className="mt-2 font-semibold">Add Note</span>
		</button>
	)

	return (
		<div
			className={cn(
				"flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-hidden pl-0 md:pl-20 transition-all",
				selectedNote && "overflow-hidden"
			)}
		>
			<Tooltip
				id="notes-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>
			<Tooltip
				id="page-help-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>

			<div className="flex-1 flex flex-col overflow-hidden relative">
				<div
					className={cn(
						"flex-1 flex flex-col overflow-y-auto custom-scrollbar transition-filter duration-500",
						selectedNote && "blur-lg brightness-75"
					)}
				>
					<HelpTooltip content="This is your digital notebook. Create notes, organize with tags, and search your thoughts. All changes are saved automatically." />
					<header className="flex-shrink-0 flex items-center justify-between p-4 md:px-8 md:py-6 sticky top-0 bg-[var(--color-primary-background)]/80 backdrop-blur-md z-10 border-b border-[var(--color-primary-surface)]">
						<div className="flex items-center gap-4">
							<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)] flex items-center gap-3">
								Notes
							</h1>
							<div className="relative">
								<IconSearch
									className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
									size={18}
								/>
								<input
									type="text"
									placeholder="Search notes..."
									value={searchQuery}
									onChange={(e) =>
										setSearchQuery(e.target.value)
									}
									className="w-full bg-[var(--color-primary-surface)] rounded-lg pl-9 pr-4 py-2 text-sm focus:ring-2 focus:ring-[var(--color-accent-blue)]"
								/>
							</div>
						</div>
						<button
							onClick={handleNewNote}
							className="px-4 py-2 flex items-center gap-2 bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white font-semibold rounded-lg text-sm transition-colors"
						>
							<IconPlus size={16} />
							<span>Add Note</span>
						</button>
					</header>

					<main className="p-4 md:p-8">
						{isLoading ? (
							<div className="flex justify-center items-center py-20">
								<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
							</div>
						) : recentNotes.length > 0 || searchQuery ? (
							recentNotes.map(([group, notes]) => (
								<div key={group} className="mb-12">
									<h2 className="text-xl font-semibold text-white mb-6">
										{group}
									</h2>
									<Reorder.Group
										axis="y"
										values={notes}
										onReorder={(newOrder) => {
											const reorderedAllNotes = [
												...allNotes
											]
											newOrder.forEach((item) => {
												const index =
													reorderedAllNotes.findIndex(
														(note) =>
															note.note_id ===
															item.note_id
													)
												if (index > -1) {
													reorderedAllNotes.splice(
														index,
														1
													)
												}
											})
											setAllNotes([
												...newOrder,
												...reorderedAllNotes
											])
										}}
										className="columns-1 md:columns-2 lg:columns-3 xl:columns-4 gap-6"
									>
										{notes.map((note) => (
											<NoteCard
												key={note.note_id}
												note={note}
												onSelect={setSelectedNote}
												onDelete={setDeletingNote}
											/>
										))}
										{group === "Today" && <AddNoteCard />}
									</Reorder.Group>
								</div>
							))
						) : (
							<div className="text-center py-20 text-neutral-500 flex flex-col items-center">
								<IconNote
									size={64}
									strokeWidth={1}
									className="text-[var(--color-text-muted)]"
								/>
								<p className="mt-4 text-xl font-semibold">
									Your notebook is empty
								</p>
								<p className="text-sm max-w-xs mt-2 text-[var(--color-text-secondary)]">
									Create your first note to capture your
									thoughts and ideas.
								</p>
							</div>
						)}
					</main>
				</div>

				<AnimatePresence>
					{selectedNote && (
						<motion.div
							key="editor-overlay"
							initial={{ opacity: 0 }}
							animate={{ opacity: 1 }}
							exit={{ opacity: 0 }}
							transition={{ duration: 0.3 }}
							className="absolute inset-0 z-20 flex justify-end"
						>
							<motion.div
								initial={{ x: "100%" }}
								animate={{ x: 0 }}
								exit={{ x: "100%" }}
								transition={{
									type: "spring",
									stiffness: 300,
									damping: 30
								}}
								className="w-full max-w-4xl h-full bg-slate-950/50 backdrop-blur-xl shadow-2xl flex flex-col border-l border-neutral-700"
							>
								<Editor
									key={selectedNote.note_id}
									note={selectedNote}
									onClose={() => setSelectedNote(null)}
									title={editorTitle}
									content={editorContent}
									onTitleChange={setEditorTitle}
									onContentChange={setEditorContent}
									saveStatus={saveStatus}
									setSaveStatus={setSaveStatus}
								/>
								{fullSelectedNote?.linked_tasks?.length > 0 && (
									<GeneratedTasksSection
										tasks={fullSelectedNote.linked_tasks}
										onTaskClick={(taskId) => {
											setSelectedNote(null) // Close note editor
											router.push(
												`/tasks?taskId=${taskId}`
											)
										}}
									/>
								)}
							</motion.div>
						</motion.div>
					)}
				</AnimatePresence>

				{deletingNote && (
					<ModalDialog
						title="Delete Note"
						description="Are you sure you want to permanently delete this note?"
						onConfirm={() => handleDeleteNote(deletingNote.note_id)}
						onCancel={() => setDeletingNote(null)}
						confirmButtonText="Delete"
						confirmButtonType="danger"
						confirmButtonIcon={IconTrash}
					/>
				)}
			</div>
		</div>
	)
}

// TipTapEditor and Editor components are assumed to be in @components/notes/Editor.js
// based on the import statement and the provided diff.

export default NotesPage
