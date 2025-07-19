"use client"

import React, { useState, useEffect } from "react"
import { Command } from "cmdk"
import {
	IconHome,
	IconChecklist,
	IconPlugConnected,
	IconAdjustments,
	IconPlus
} from "@tabler/icons-react"
import { useRouter } from "next/navigation"

const CommandPalette = ({ open, setOpen }) => {
	const router = useRouter()

	useEffect(() => {
		const down = (e) => {
			if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
				e.preventDefault()
				setOpen((open) => !open)
			}
		}
		document.addEventListener("keydown", down)
		return () => document.removeEventListener("keydown", down)
	}, [setOpen])

	const runCommand = (command) => {
		setOpen(false)
		command()
	}

	return (
		<Command.Dialog
			open={open}
			onOpenChange={setOpen}
			label="Global Command Menu"
		>
			<Command.Input placeholder="Type a command or search..." />
			<Command.List>
				<Command.Empty>No results found.</Command.Empty>

				<Command.Group heading="Navigation">
					<Command.Item
						onSelect={() => runCommand(() => router.push("/home"))}
					>
						<IconHome className="mr-2 h-4 w-4" />
						Go to Home
					</Command.Item>
					<Command.Item
						onSelect={() => runCommand(() => router.push("/tasks"))}
					>
						<IconChecklist className="mr-2 h-4 w-4" />
						Go to Tasks
					</Command.Item>
					<Command.Item
						onSelect={() =>
							runCommand(() => router.push("/integrations"))
						}
					>
						<IconPlugConnected className="mr-2 h-4 w-4" />
						Go to Integrations
					</Command.Item>
					<Command.Item
						onSelect={() =>
							runCommand(() => router.push("/settings"))
						}
					>
						<IconAdjustments className="mr-2 h-4 w-4" />
						Go to Settings
					</Command.Item>
				</Command.Group>

				<Command.Group heading="Actions">
					<Command.Item
						onSelect={() => {
							runCommand(() => router.push("/tasks?action=add"))
						}}
					>
						<IconPlus className="mr-2 h-4 w-4" />
						New Task
					</Command.Item>
				</Command.Group>
			</Command.List>
		</Command.Dialog>
	)
}

export default CommandPalette
