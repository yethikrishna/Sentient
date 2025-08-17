"use client"
import React from "react"
import { motion } from "framer-motion"
import {
	IconSparkles,
	IconMail,
	IconCalendar,
	IconFileText,
	IconX,
	IconBrandSlack,
	IconBrandNotion,
	IconBrandGithub,
	IconBrandGoogleDrive,
	IconWorldSearch,
	IconUsers
} from "@tabler/icons-react"

const toolIcons = {
	gmail: IconMail,
	gcalendar: IconCalendar,
	gdocs: IconFileText,
	gdrive: IconBrandGoogleDrive,
	gpeople: IconUsers,
	slack: IconBrandSlack,
	notion: IconBrandNotion,
	github: IconBrandGithub,
	internet_search: IconWorldSearch
}

const exampleWorkflows = [
	{
		title: "Daily Briefing",
		description:
			"Get a summary of your unread emails and today's calendar events.",
		prompt: "Every morning at 8 AM, send me a summary of unread emails and my upcoming calendar events for the day on WhatsApp.",
		tools: ["gmail", "gcalendar"]
	},
	{
		title: "Meeting Prep",
		description:
			"Find all relevant documents and emails about an upcoming meeting.",
		prompt: "Help me prepare for my meeting with Acme Corp tomorrow. Find all recent emails and documents related to them.",
		tools: ["gcalendar", "gmail", "gdrive"]
	},
	{
		title: "Schedule a Follow-up",
		description: "Find a time and schedule a meeting with a contact.",
		prompt: "Find a free slot on my Google Calendar for next week and schedule a follow-up call with jane.doe@example.com now.",
		tools: ["gcalendar", "gpeople"]
	},
	{
		title: "Weekly Lead Nurturing",
		description:
			"Draft personalized follow-up emails for new leads from Google Contacts.",
		prompt: "Every Monday morning, find all contacts in my Google Contacts with the label 'Q3-Leads'. For each contact, search my gmail to see if we have discussed anything before. If not, draft a friendly, personalized outreach email asking if they would be open to collaborating and suggest a brief call.",
		tools: ["gpeople", "gmail"]
	},
	{
		title: "Content Idea Generation",
		description:
			"Research trends and populate your Notion database with new content ideas.",
		prompt: "Every Friday, find the top 5 news articles from the past week in the 'technology' category. Also, perform an internet search for 'latest trends in AI productivity tools'. Summarize the key findings and add them as new ideas to the 'Content Ideas for The Week' Page under the Getting Started page in Notion.",
		tools: ["internet_search", "notion"]
	},
	{
		title: "Automated Meeting Agenda",
		description:
			"Generate a meeting agenda by summarizing recent activity from GitHub and Slack.",
		prompt: "We have a project sync meeting every Friday at 5PM. Every Friday at 4 PM, summarize all closed issues in the 'Project-Sentient' GitHub repo from the last 7 days. Check the Trello board for Project-Sentient and see what the remaining cards on the 'To-Do' board are. Create a new Google Doc with this summary and outline what we can discuss in the meeting. Share this document with the team on Slack. Add a Google Calendar event for the meeting with the agenda attached.",
		tools: ["gcalendar", "github", "slack", "gdocs"]
	}
]

const WelcomePanel = ({ onExampleClick, onClose }) => {
	return (
		<div className="p-4 md:p-6 h-full flex flex-col">
			<header className="flex items-start justify-between text-center mb-6 md:mb-8 flex-shrink-0">
				<div className="flex-1 flex flex-col items-center">
					<IconSparkles
						size={32}
						className="text-brand-orange mb-3"
					/>
					<h2 className="text-xl md:text-2xl font-bold text-white">
						Welcome to Tasks
					</h2>
					<p className="text-neutral-400 mt-1 text-sm md:text-base max-w-lg">
						This is your command center for getting things done.
						Simply describe what you need in the input box below.
						You can create one-time tasks, scheduled actions, or
						recurring workflows using natural language.
					</p>
				</div>
				{/* Mobile-only close button */}
				<button
					onClick={onClose}
					className="p-2 text-neutral-400 hover:text-white md:hidden -mr-2 -mt-2"
				>
					<IconX size={20} />
				</button>
			</header>
			<div className="space-y-4 overflow-y-auto custom-scrollbar flex-1">
				<h3 className="font-semibold text-neutral-300 px-2">
					Example Workflows
				</h3>
				{exampleWorkflows.map((workflow, index) => (
					<motion.div
						key={workflow.title}
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ delay: index * 0.1 }}
						onClick={() => onExampleClick(workflow.prompt)}
						className="bg-neutral-800/50 p-4 rounded-lg border border-neutral-700 hover:border-brand-orange cursor-pointer transition-colors flex flex-col justify-between"
					>
						<div>
							<div className="flex items-center gap-3 mb-2">
								<div className="flex -space-x-2">
									{workflow.tools.map((toolName) => {
										const Icon =
											toolIcons[toolName] || IconSparkles
										return (
											<div
												key={toolName}
												className="w-8 h-8 rounded-full flex items-center justify-center border-2 border-neutral-900 bg-white text-black"
											>
												<Icon size={16} />
											</div>
										)
									})}
								</div>
								<h4 className="font-semibold text-white">
									{workflow.title}
								</h4>
							</div>
							<p className="text-sm text-neutral-400">
								{workflow.description}
							</p>
						</div>
					</motion.div>
				))}
			</div>
		</div>
	)
}

export default WelcomePanel
