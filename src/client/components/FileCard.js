"use client"

import React from "react"
import { IconFile, IconDownload } from "@tabler/icons-react"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"

const FileCard = ({ filename }) => {
	const handleDownload = async () => {
		const toastId = toast.loading(`Downloading ${filename}...`)
		try {
			const response = await fetch(
				`/api/files/download/${encodeURIComponent(filename)}`
			)

			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Download failed")
			}

			const blob = await response.blob()
			const url = window.URL.createObjectURL(blob)
			const a = document.createElement("a")
			a.href = url
			a.download = filename
			document.body.appendChild(a)
			a.click()
			a.remove()
			window.URL.revokeObjectURL(url)
			toast.success(`${filename} downloaded.`, { id: toastId })
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: toastId })
		}
	}

	return (
		<div
			className={cn(
				"my-2 flex items-center justify-between gap-3 rounded-lg border border-neutral-700 bg-neutral-800/60 p-3"
			)}
		>
			<div className="flex items-center gap-3 overflow-hidden">
				<IconFile
					size={24}
					className="flex-shrink-0 text-neutral-400"
				/>
				<span
					className="truncate font-mono text-sm text-white"
					title={filename}
				>
					{filename}
				</span>
			</div>
			<button
				onClick={handleDownload}
				className="flex-shrink-0 rounded-md bg-blue-600 p-2 text-white hover:bg-blue-500"
				title={`Download ${filename}`}
			>
				<IconDownload size={16} />
			</button>
		</div>
	)
}

export default FileCard
