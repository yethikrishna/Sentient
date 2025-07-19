"use client"

import React, { Fragment } from "react"
import { useEditor, EditorContent, BubbleMenu } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import {
	IconBold,
	IconItalic,
	IconH1,
	IconH2,
	IconH3,
	IconList,
	IconListNumbers,
	IconBlockquote
} from "@tabler/icons-react"
import { cn } from "@utils/cn"

const Editor = ({ content, onUpdate, title, onTitleUpdate }) => {
	const editor = useEditor({
		extensions: [
			StarterKit.configure({
				heading: {
					levels: [1, 2, 3]
				}
			}),
			Placeholder.configure({
				placeholder: "Let your ideas flow..."
			})
		],
		content: content,
		onUpdate: ({ editor }) => {
			onUpdate(editor.getHTML())
		},
		editorProps: {
			attributes: {
				class: "prose prose-invert focus:outline-none max-w-full"
			}
		}
	})

	const BubbleMenuItem = ({ icon: Icon, onClick, isActive = false }) => (
		<button
			onClick={onClick}
			className={cn(
				"p-2 text-white hover:bg-dark-surface-elevated rounded-md",
				isActive && "bg-sentient-blue text-white"
			)}
		>
			<Icon className="w-5 h-5" />
		</button>
	)

	return (
		<div className="flex-1 flex flex-col p-4 md:p-8">
			<input
				type="text"
				value={title}
				onChange={(e) => onTitleUpdate(e.target.value)}
				placeholder="Untitled Note"
				className="w-full bg-transparent text-3xl md:text-4xl font-bold focus:outline-none text-white placeholder-neutral-600 mb-6"
			/>
			{editor && (
				<BubbleMenu
					editor={editor}
					tippyOptions={{ duration: 100 }}
					className="bg-dark-surface p-2 rounded-lg shadow-xl border border-dark-surface-elevated flex gap-1"
				>
					<BubbleMenuItem
						icon={IconBold}
						onClick={() =>
							editor.chain().focus().toggleBold().run()
						}
						isActive={editor.isActive("bold")}
					/>
					<BubbleMenuItem
						icon={IconItalic}
						onClick={() =>
							editor.chain().focus().toggleItalic().run()
						}
						isActive={editor.isActive("italic")}
					/>
					<div className="w-px bg-dark-surface-elevated mx-1" />
					<BubbleMenuItem
						icon={IconH1}
						onClick={() =>
							editor
								.chain()
								.focus()
								.toggleHeading({ level: 1 })
								.run()
						}
						isActive={editor.isActive("heading", { level: 1 })}
					/>
					<BubbleMenuItem
						icon={IconH2}
						onClick={() =>
							editor
								.chain()
								.focus()
								.toggleHeading({ level: 2 })
								.run()
						}
						isActive={editor.isActive("heading", { level: 2 })}
					/>
					<div className="w-px bg-dark-surface-elevated mx-1" />
					<BubbleMenuItem
						icon={IconList}
						onClick={() =>
							editor.chain().focus().toggleBulletList().run()
						}
						isActive={editor.isActive("bulletList")}
					/>
					<BubbleMenuItem
						icon={IconBlockquote}
						onClick={() =>
							editor.chain().focus().toggleBlockquote().run()
						}
						isActive={editor.isActive("blockquote")}
					/>
				</BubbleMenu>
			)}
			<EditorContent
				editor={editor}
				className="flex-1 overflow-y-auto custom-scrollbar"
			/>
		</div>
	)
}

export default Editor
