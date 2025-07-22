"use client"

import React from "react"
import { useRouter } from "next/navigation"
import { IconPlugConnected } from "@tabler/icons-react"

const ConnectToolButton = ({ toolName }) => {
	const router = useRouter()
	return (
		<button
			onClick={() => router.push(`/integrations`)}
			className="text-xs self-start bg-yellow-500/20 text-yellow-300 font-semibold py-1 px-2 rounded-full hover:bg-yellow-500/40 transition-colors whitespace-nowrap flex items-center gap-1"
		>
			<IconPlugConnected size={12} />
			Connect {toolName}
		</button>
	)
}

export default ConnectToolButton
