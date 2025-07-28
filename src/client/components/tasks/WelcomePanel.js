"use client"
import React from "react"
import { motion } from "framer-motion"
import {
	IconSparkles,
	IconMail,
	IconCalendar,
	IconFileText,
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
		prompt: "Give me a daily briefing of my unread important emails and today's schedule.",
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
		prompt: "Find a time to schedule a 30-minute follow-up call with jane.doe@example.com for next week.",
		tools: ["gcalendar", "gpeople"]
	},
	{
		title: "Weekly Lead Nurturing",
		description:
			"Draft personalized follow-up emails for new leads from Google Contacts.",
		prompt: "Every Monday morning, find all contacts in my Google Contacts with the label 'Q3-Leads'. For each contact, check my Gmail to see if we've communicated in the last 10 days. If not, draft a friendly, personalized follow-up email asking if they have any questions about our last conversation and suggesting a brief call.",
		tools: ["gpeople", "gmail"]
	},
	{
		title: "Content Idea Generation",
		description:
			"Research trends and populate your Notion database with new content ideas.",
		prompt: "Every Friday, find the top 5 news articles from the past week in the 'technology' category. Also, perform an internet search for 'latest trends in AI productivity tools'. Summarize the key findings and add them as new ideas to my 'Content Ideas' database in Notion.",
		tools: ["internet_search", "notion"]
	},
	{
		title: "Automated Meeting Agenda",
		description:
			"Generate a meeting agenda by summarizing recent activity from GitHub and Slack.",
		prompt: "An hour before our weekly 'Project Phoenix Sync' meeting, prepare the agenda. Summarize all new commits and closed issues in the 'Project-Phoenix' GitHub repo from the last 7 days. Check the '#project-phoenix' Slack channel for any messages containing 'blocker' or 'help'. Create a new Google Doc with this summary and a template for meeting notes.",
		tools: ["gcalendar", "github", "slack", "gdocs"]
	}
]

const WelcomePanel = ({ onExampleClick }) => {
	return (
		<div className="p-6 h-full flex flex-col">
			<div className="text-center mb-8">
				<IconSparkles
					size={40}
					className="mx-auto text-sentient-blue mb-4"
				/>
				<h2 className="text-2xl font-bold text-white">
					Welcome to Tasks
				</h2>
				<p className="text-neutral-400 mt-2">
					Select a task to see its details or start with an example
					workflow.
				</p>
			</div>
			<div className="space-y-4">
				<h3 className="font-semibold text-neutral-300">
					Example Workflows
				</h3>
				{exampleWorkflows.map((workflow, index) => (
					<motion.div
						key={workflow.title}
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ delay: index * 0.1 }}
						onClick={() => onExampleClick(workflow.prompt)}
						className="bg-neutral-800/50 p-4 rounded-lg border border-neutral-700 hover:border-sentient-blue cursor-pointer transition-colors flex flex-col justify-between"
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
