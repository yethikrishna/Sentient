import {
	IconClock,
	IconRefresh,
	IconCircleCheck,
	IconAlertCircle,
	IconArchive,
	IconMailQuestion,
	IconMessageQuestion,
	IconPlayerPlay,
	IconX,
	IconHelpCircle
} from "@tabler/icons-react"

export const taskStatusColors = {
	planning: {
		icon: IconRefresh,
		label: "Planning",
		color: "text-blue-400",
		border: "border-blue-400"
	},
	pending: {
		icon: IconClock,
		label: "Pending",
		color: "text-yellow-400",
		border: "border-yellow-400"
	},
	approval_pending: {
		icon: IconMailQuestion,
		label: "Pending Approval",
		color: "text-purple-400",
		border: "border-purple-400"
	},
	clarification_pending: {
		icon: IconMessageQuestion,
		label: "Needs Input",
		color: "text-orange-400",
		border: "border-orange-400"
	},
	clarification_answered: {
		icon: IconRefresh,
		label: "Re-planning",
		color: "text-blue-400",
		border: "border-blue-400"
	},
	processing: {
		icon: IconPlayerPlay,
		label: "Processing",
		color: "text-blue-400",
		border: "border-blue-400"
	},
	active: {
		icon: IconRefresh,
		label: "Active",
		color: "text-green-400",
		border: "border-green-400"
	},
	completed: {
		icon: IconCircleCheck,
		label: "Completed",
		color: "text-green-400",
		border: "border-green-400"
	},
	error: {
		icon: IconAlertCircle,
		label: "Error",
		color: "text-red-400",
		border: "border-red-400"
	},
	cancelled: {
		icon: IconX,
		label: "Cancelled",
		color: "text-gray-500",
		border: "border-gray-500"
	},
	archived: {
		icon: IconArchive,
		label: "Archived",
		color: "text-gray-500",
		border: "border-gray-500"
	},
	default: {
		icon: IconHelpCircle,
		label: "Unknown",
		color: "text-gray-400",
		border: "border-gray-400"
	}
}

export const priorityMap = {
	0: { label: "High", color: "text-red-400" },
	1: { label: "Medium", color: "text-yellow-400" },
	2: { label: "Low", color: "text-gray-400" },
	default: { label: "Medium", color: "text-yellow-400" }
}
