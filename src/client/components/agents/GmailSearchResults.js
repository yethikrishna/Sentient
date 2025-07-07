import { useState } from "react" // Importing useState hook from React for managing component state
import {
	IconMail, // Icon for email
	IconUser, // Icon for user/sender
	IconChevronDown, // Icon for dropdown chevron (down)
	IconChevronUp, // Icon for dropdown chevron (up)
	IconExternalLink // Icon for external link
} from "@tabler/icons-react" // Importing icons from tabler-icons-react library
import React from "react"

/**
 * EmailItem Component - Displays a summarized view of an email in a list.
 *
 * This component renders a single email item with details like subject, sender, and a snippet.
 * It includes an expandable section to show the full email body and a toggle button to expand/collapse the body.
 *
 * @param {object} props - Component props.
 * @param {object} props.email - An object containing the email details.
 * @param {string} props.email.subject - The subject of the email.
 * @param {string} props.email.from - The sender's email address or name.
 * @param {string} props.email.snippet - A brief preview of the email content.
 * @param {string} props.email.body - The full body content of the email.
 *
 * @returns {React.ReactNode} - The EmailItem component UI.
 */
const EmailItem = ({ email }) => {
	// State to manage the expanded/collapsed state of the email body - expanded: boolean
	const [expanded, setExpanded] = useState(false)

	/**
	 * Toggles the expanded state of the email body.
	 *
	 * Sets the `expanded` state to the opposite of its current value, effectively toggling the visibility
	 * of the full email body within the EmailItem component.
	 *
	 * @function handleToggle
	 * @returns {void}
	 */
	const handleToggle = () => setExpanded(!expanded) // Toggles the 'expanded' state

	return (
		<li className="p-4 bg-[var(--color-primary-background)] rounded-md border border-[var(--color-primary-surface-elevated)] hover:border-[var(--color-accent-blue)] transition-colors">
			{/* Main container for each email item */}
			<div className="flex justify-between items-center">
				{/* Left side container for email summary info */}
				<div className="flex flex-col">
					{/* Subject line with email icon */}
					<div className="flex items-center space-x-2">
						<IconMail className="w-5 h-5 text-[var(--color-accent-blue)]" />
						<span className="text-[var(--color-text-primary)] font-semibold">
							{email.subject}
						</span>
					</div>
					{/* Sender info with user icon */}
					<div className="flex items-center space-x-2 mt-1">
						<IconUser className="w-4 h-4 text-[var(--color-text-secondary)]" />
						<span className="text-[var(--color-text-secondary)] text-sm">
							From: {email.from}
						</span>
					</div>
					{/* Email snippet (preview) */}
					<div className="mt-1">
						<p className="text-[var(--color-text-secondary)] text-sm line-clamp-2">
							{email.snippet}
						</p>
					</div>
				</div>
				{/* Right side container for expand/collapse toggle button */}
				<div className="flex items-center space-x-2">
					<button
						onClick={handleToggle} // Call handleToggle function on button click
						className="text-[var(--color-accent-blue)] hover:text-white"
						title="Show Details"
					>
						{/* Conditional rendering of chevron icon based on 'expanded' state */}
						{expanded ? (
							<IconChevronUp className="w-5 h-5" /> // Show ChevronUp icon when expanded is true
						) : (
							<IconChevronDown className="w-5 h-5" /> // Show ChevronDown icon when expanded is false
						)}
					</button>
				</div>
			</div>
			{/* Expanded email body section, conditionally rendered based on 'expanded' state */}
			{expanded && (
				<div className="mt-3 border-t border-[var(--color-primary-surface-elevated)] pt-3">
					<p className="text-[var(--color-text-primary)] text-sm whitespace-pre-wrap">
						{email.body}
					</p>
				</div>
			)}
		</li>
	)
}

/**
 * GmailSearchResults Component - Displays a list of Gmail search results.
 *
 * This component takes an array of emails and a Gmail search URL as props.
 * It renders a list of EmailItem components for each email and provides a button to open the full search results in Gmail in a new tab.
 * If no emails are found, it displays a "No emails found" message.
 *
 * @param {object} props - Component props.
 * @param {Array<object>} props.emails - An array of email objects representing search results.
 * @param {string} props.gmailSearchUrl - The URL to open the Gmail search results in a browser.
 *
 * @returns {React.ReactNode} - The GmailSearchResults component UI.
 */
const GmailSearchResults = ({ emails, gmailSearchUrl }) => {
	/**
	 * Opens the Gmail search URL in a new tab.
	 *
	 * When the "Open search in Gmail" button is clicked, this function opens the provided `gmailSearchUrl`
	 * in a new browser tab. It uses `window.open` with `noopener noreferrer` for security and to prevent
	 * the new page from having access to the opener page.
	 *
	 * @function openSearchInGmail
	 * @returns {void}
	 */
	const openSearchInGmail = () => {
		if (gmailSearchUrl) {
			window.open(gmailSearchUrl, "_blank", "noopener noreferrer") // Opens gmailSearchUrl in a new tab
		}
	}

	return (
		<div className="w-full bg-[var(--color-primary-surface)] rounded-lg p-4 mb-4 border border-[var(--color-accent-blue)]">
			{/* Header section of the Gmail Search Results card */}
			<div className="flex items-center gap-2 mb-4">
				<IconMail className="w-6 h-6 text-[var(--color-accent-blue)]" />
				<h3 className="text-xl font-semibold text-[var(--color-text-primary)]">
					Gmail Search Results
				</h3>
			</div>
			{/* Button to open search in Gmail */}
			<div className="mb-4">
				<button
					onClick={openSearchInGmail} // Call openSearchInGmail function on button click
					className="flex items-center gap-2 px-3 py-2 bg-[var(--color-accent-blue)] text-white rounded-md hover:bg-[var(--color-accent-blue-hover)] transition-colors"
				>
					<IconExternalLink className="w-5 h-5" />
					<span className="text-sm">Open search in Gmail</span>
				</button>
			</div>
			{/* Conditional rendering of email list or "No emails found" message */}
			{emails && emails.length > 0 ? (
				<ul className="space-y-4">
					{/* Map through emails array and render EmailItem for each email */}
					{emails.map((email, index) => (
						<EmailItem key={index} email={email} />
					))}
				</ul>
			) : (
				// Displayed when no emails are found
				<div className="text-[var(--color-text-primary)]">
					No emails found.
				</div>
			)}
		</div>
	)
}

export default GmailSearchResults
