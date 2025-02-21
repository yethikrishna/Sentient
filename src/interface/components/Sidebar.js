"use client"

import { useRouter } from "next/navigation" // Importing useRouter hook from next/navigation for client-side routing
import { useEffect, useState } from "react" // Importing React hooks: useEffect, useState
import {
	IconChevronRight, // Icon for chevron right arrow
	IconDotsVertical, // Icon for vertical dots (more options)
	IconUser, // Icon for user profile
	IconHome, // Icon for home navigation
	IconLogout, // Icon for logout action
	IconSettings, // Icon for settings action
	IconEdit, // Icon for edit action
	IconTrash // Icon for trash/delete action
} from "@tabler/icons-react" // Importing icons from tabler-icons-react library
import SlideButton from "./SlideButton" // Importing SlideButton component
import EncryptButton from "./EncryptButton" // Importing EncryptButton component
import Speeddial from "./SpeedDial" // Importing Speeddial component
import toast from "react-hot-toast" // Library for displaying toast notifications
import ModalDialog from "./ModalDialog" // Importing ModalDialog component
import React from "react"

/**
 * Sidebar Component - Navigation sidebar for the application.
 *
 * This component renders the main sidebar of the application, providing navigation links,
 * chat list, user profile information, and action buttons like settings and logout.
 * It's designed to be responsive and can be toggled to be hidden or visible, with smooth transitions.
 *
 * @param {object} props - Component props.
 * @param {object} props.userDetails - User details object, containing user profile information.
 * @param {function} props.setSidebarVisible - Function to control sidebar visibility from parent components.
 * @param {boolean} props.isSidebarVisible - Boolean indicating if the sidebar is currently visible.
 * @param {string} props.chatId - Current chat ID, used for chat navigation and context.
 * @param {function} props.setChatId - Function to set current chat ID, used for chat navigation.
 * @param {boolean} props.fromChat - Boolean flag to indicate if the sidebar is in chat context.
 * @returns {React.ReactNode} - The Sidebar component UI.
 */
const Sidebar = ({
	userDetails,
	setSidebarVisible,
	isSidebarVisible,
	chatId,
	setChatId,
	fromChat
}) => {
	const router = useRouter() // Hook to get the router object for navigation
	// State to store chat list - chats: any[]
	const [chats, setChats] = useState([])
	// State to control visibility of rename dialog - isRenameDialogOpen: boolean
	const [isRenameDialogOpen, setIsRenameDialogOpen] = useState(false)
	// State to control visibility of delete dialog - isDeleteDialogOpen: boolean
	const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
	// State to store currently selected chat for rename/delete actions - currentChat: any
	const [currentChat, setCurrentChat] = useState(null)
	// State for new chat name input in rename dialog - newChatName: string
	const [newChatName, setNewChatName] = useState("")

	/**
	 * Toggles the visibility of the user menu dropdown.
	 *
	 * This function toggles the 'hidden' class on the user menu element to show or hide it.
	 * It also dynamically sets the width of the user menu content to match the width of the user profile section,
	 * ensuring the dropdown menu aligns correctly with the profile section.
	 *
	 * @function toggleUserMenu
	 * @returns {void}
	 */
	const toggleUserMenu = () => {
		const userMenu = document.getElementById("user-menu") // Get user menu element by ID
		const userProfile = document.getElementById("user-profile") // Get user profile element by ID
		const userMenuContent = document.getElementById("user-menu-content") // Get user menu content element by ID

		if (userMenu) {
			userMenu.classList.toggle("hidden") // Toggle 'hidden' class to show/hide user menu

			if (!userMenu.classList.contains("hidden")) {
				userMenuContent.style.width = `${userProfile.offsetWidth}px` // Set user menu content width to user profile width for alignment
			}
		}
	}

	/**
	 * Fetches the list of chats from the backend.
	 *
	 * Uses electron invoke to call the backend function to retrieve the chat list and updates the `chats` state.
	 * Handles errors by displaying a toast notification.
	 *
	 * @async
	 * @function fetchChats
	 * @returns {Promise<void>}
	 */
	const fetchChats = async () => {
		try {
			const response = await window.electron?.invoke("get-chats") // Invoke electron backend to get chat list
			if (response?.data?.chats) {
				setChats(response.data.chats) // Update chats state with fetched chat list
			}
		} catch (error) {
			toast.error(`Error fetching chats: ${error}`) // Show error toast if fetching fails
		}
	}

	/**
	 * Logs the user out of the application.
	 *
	 * Calls the electron backend function to log the user out. This function is intended to handle
	 * the backend logout process, which might include clearing sessions or tokens.
	 *
	 * @async
	 * @function logout
	 * @returns {Promise<void>}
	 */
	const logout = async () => {
		await window.electron.logOut() // Invoke electron backend to log out user
	}

	/**
	 * useEffect hook to fetch chats list when component mounts or chatId changes.
	 *
	 * Fetches the list of chats by calling `fetchChats` function when the component is first rendered
	 * and whenever the `chatId` state changes. This ensures that the chat list is updated when a new chat is selected or created.
	 */
	useEffect(() => {
		fetchChats() // Fetch chats list on component mount and chatId change
	}, [chatId]) // Dependency array: effect runs when chatId changes

	/**
	 * Handles navigation to a specific chat or home.
	 *
	 * Navigates the user to the chat interface with the specified chatId. If `fromChat` prop is true,
	 * it only updates the `chatId` state, assuming the component is already within the chat interface.
	 * Otherwise, it uses next/navigation router to push a new route to the chat page with the chatId as a query parameter.
	 *
	 * @function handleChatNavigation
	 * @param {string} id - The ID of the chat to navigate to, or 'home' for the home screen.
	 * @returns {void}
	 */
	const handleChatNavigation = (id) => {
		if (fromChat) {
			setChatId(id) // If fromChat is true, only update chatId state
		} else {
			router.push(`/chat?chatId=${id}`) // Navigate to chat page with chatId as query parameter
		}
	}

	/**
	 * Handles renaming a chat.
	 *
	 * Invokes the electron backend to rename a chat with the given ID and new name.
	 * After successful renaming, it refetches the chat list, closes the rename dialog,
	 * clears the new chat name input, and displays a success toast notification.
	 * Handles errors by displaying an error toast notification.
	 *
	 * @async
	 * @function handleRenameChat
	 * @param {string} id - The ID of the chat to rename.
	 * @param {string} newName - The new name for the chat.
	 * @returns {Promise<void>}
	 */
	const handleRenameChat = async (id, newName) => {
		try {
			await window.electron?.invoke("rename-chat", { id, newName }) // Invoke electron backend to rename chat
			await fetchChats() // Refetch chat list to update sidebar
			setIsRenameDialogOpen(false) // Close rename dialog
			setNewChatName("") // Clear new chat name input
			toast.success("Chat renamed successfully") // Show success toast
		} catch (error) {
			toast.error(`Error renaming chat: ${error}`) // Show error toast if renaming fails
		}
	}

	/**
	 * Handles deleting a chat.
	 *
	 * Invokes the electron backend to delete a chat with the given ID.
	 * After successful deletion, it refetches the chat list, closes the delete dialog,
	 * displays a success toast notification, and navigates the user to the home screen by setting chatId to 'home'.
	 * Handles errors by displaying an error toast notification.
	 *
	 * @async
	 * @function handleDeleteChat
	 * @param {string} id - The ID of the chat to delete.
	 * @returns {Promise<void>}
	 */
	const handleDeleteChat = async (id) => {
		try {
			await window.electron?.invoke("delete-chat", { id }) // Invoke electron backend to delete chat
			fetchChats() // Refetch chat list to update sidebar
			setIsDeleteDialogOpen(false) // Close delete dialog
			toast.success("Chat deleted successfully") // Show success toast
			setChatId("home") // Navigate to home screen after deletion
		} catch (error) {
			toast.error(`Error deleting chat: ${error}`) // Show error toast if deletion fails
		}
	}

	// Speed dial actions configuration for the bottom right speed dial menu
	const speedDialActions = [
		{
			label: "Profile", // Label for the Profile action
			action: () => router.push("/profile"), // Action to navigate to the profile page
			icon: <IconUser className="w-6 h-6" /> // Icon for the Profile action
		},
		{
			label: "Settings", // Label for the Settings action
			action: () => router.push("/settings"), // Action to navigate to the settings page
			icon: <IconSettings className="w-6 h-6" /> // Icon for the Settings action
		},
		{
			label: "Logout", // Label for the Logout action
			action: logout, // Action to perform logout
			icon: <IconLogout className="w-6 h-6" /> // Icon for the Logout action
		}
	]

	/**
	 * Main return statement for the Sidebar component, rendering the sidebar UI.
	 *
	 * Includes sidebar container, logo and title, navigation links, chat list with EncryptButton for each chat,
	 * user profile section with user details and dropdown menu, speed dial menu for additional actions,
	 * and modal dialogs for renaming and deleting chats.
	 *
	 * @returns {React.ReactNode} - The main UI for the Sidebar component.
	 */
	return (
		<>
			{/* Sidebar container */}
			<div
				id="sidebar"
				className={`w-1/5 h-full flex flex-col justify-center bg-smokeblack overflow-y-scroll no-scrollbar transform transition-all duration-300 ${
					isSidebarVisible
						? "translate-x-0 opacity-100 z-40 pointer-events-auto" // Styles for visible sidebar: slide in from left, full opacity, z-index, pointer events enabled
						: "-translate-x-full opacity-0 z-0 pointer-events-none" // Styles for hidden sidebar: slide out to left, zero opacity, z-index 0, pointer events disabled
				}`}
				onMouseLeave={() => setSidebarVisible(false)} // Hide sidebar on mouse leave
			>
				{/* Logo and title section */}
				<div className="flex items-center justify-center px-2 md:px-10 py-1 w-full h-[25%]">
					<img
						src="/images/half-logo-dark.svg" // Path to the logo image
						alt="Logo" // Alt text for accessibility
						style={{ width: "40px", height: "40px" }} // Inline styles for logo size
					/>
					<span className="text-3xl text-white font-normal ml-4">
						Sentient
					</span>{" "}
					{/* Application title */}
				</div>

				{/* Navigation links and chats section */}
				<div className="flex flex-col gap-6 mt-4 p-4 h-[65%]">
					{/* Home navigation button */}
					<SlideButton
						onClick={() => handleChatNavigation("home")} // Navigate to home on click
						primaryColor="#000000" // Primary color for the button
						className="mb-4 cursor-pointer" // Margin bottom for spacing
						text="Home" // Button text - Home
						icon={<IconHome className="w-5 h-5" />} // Home icon
					/>

					{/* "Your Chats" section header */}
					<h2 className="text-lg text-white font-semibold mb-2">
						Your Chats
					</h2>
					{/* Chat list container */}
					<ul className="space-y-2 flex flex-col gap-3 overflow-x-hidden overflow-y-scroll no-scrollbar">
						{/* Map through chats array and render EncryptButton for each chat */}
						{chats.map((chat) => (
							<EncryptButton
								onClick={() => handleChatNavigation(chat.id)} // Navigate to chat on click
								className="w-full text-sm text-black bg-white rounded-lg p-2 cursor-pointer border border-black hover:border-white hover:bg-black hover:text-white transition relative"
								// EncryptButton styling: full width, small text, black text color, white background, rounded corners, padding, cursor, borders, hover effects, transition, relative positioning
								onEdit={() => {
									setCurrentChat(chat) // Set current chat for rename action
									setIsRenameDialogOpen(true) // Open rename dialog
								}}
								onDelete={() => {
									setCurrentChat(chat) // Set current chat for delete action
									setIsDeleteDialogOpen(true) // Open delete dialog
								}}
								key={chat.id} // Key prop for React list rendering
							>
								{chat.title} {/* Chat title as button text */}
							</EncryptButton>
						))}
					</ul>
				</div>
				{/* User profile section at the bottom of sidebar */}
				<div
					className="flex flex-row justify-start items-center w-3/4 space-x-8 relative rounded-xl px-5 py-2 h-[10%]"
					id="user-profile"
					style={{ position: "sticky", bottom: "0", zIndex: 30 }} // Sticky positioning at the bottom, higher z-index
				>
					{/* User profile picture or icon */}
					<div className="rounded-full overflow-hidden w-12 h-12 mr-5 shrink-0">
						{userDetails["picture"] ? (
							<img
								src={userDetails["picture"]} // User profile picture URL from userDetails
								alt="User" // Alt text for accessibility
								className="w-full h-full object-cover cursor-pointer" // Image styling: full width and height, object cover, cursor pointer
								onClick={() => toggleUserMenu()} // Toggle user menu on click
							/>
						) : (
							<IconUser className="w-full h-full object-cover cursor-pointer" />
							// IconUser as fallback if no picture, full width and height, object cover, cursor pointer
						)}
					</div>
					{/* User's given name, clickable to toggle user menu */}
					<p
						className="text-lg text-white cursor-pointer" // Text styling: large text size, white text color, cursor pointer
						onClick={() => toggleUserMenu()} // Toggle user menu on click
					>
						{userDetails["given_name"]}{" "}
						{/* Display user's given name */}
					</p>
				</div>

				{/* Speed dial menu for additional actions, positioned at the bottom right */}
				<div className="absolute right-4 bottom-2 flex flex-row items-center">
					<Speeddial
						icon={<IconDotsVertical />}
						direction="up"
						actionButtons={speedDialActions}
						tooltipPosition="left"
					/>
				</div>
			</div>

			{/* Chevron icon to toggle sidebar visibility, positioned at the left edge */}
			<div
				className="absolute top-0 left-0 bg-matteblack w-[5%] h-full z-10 flex items-center justify-start"
				onMouseEnter={() => setSidebarVisible(true)} // Show sidebar on mouse enter
			>
				<div className="ml-3">
					<IconChevronRight className="text-white w-6 h-6 animate-pulse font-bold" />
					{/* Chevron right icon, white color, size, pulse animation, bold font weight */}
				</div>
			</div>

			{/* Modal dialog for renaming chat, conditionally rendered based on isRenameDialogOpen state */}
			{isRenameDialogOpen && (
				<ModalDialog
					title="Rename Chat" // Modal title - Rename Chat
					inputPlaceholder="Enter new chat name" // Input placeholder text
					inputValue={newChatName} // Input value from newChatName state
					onInputChange={setNewChatName} // Handler to update newChatName state
					onCancel={() => setIsRenameDialogOpen(false)} // Handler to close rename dialog
					onConfirm={() =>
						handleRenameChat(currentChat.id, newChatName)
					} // Handler to confirm rename action
					confirmButtonText="Rename" // Confirm button text - Rename
					confirmButtonColor="bg-lightblue" // Confirm button background color - lightblue
					confirmButtonBorderColor="border-lightblue" // Confirm button border color - lightblue
					confirmButtonIcon={IconEdit} // Confirm button icon - Edit icon
					showInput={true} // Show input field in modal
				/>
			)}

			{/* Modal dialog for deleting chat, conditionally rendered based on isDeleteDialogOpen state */}
			{isDeleteDialogOpen && (
				<ModalDialog
					title="Delete Chat" // Modal title - Delete Chat
					description="Are you sure you want to delete this chat?" // Modal description - confirmation question
					onCancel={() => setIsDeleteDialogOpen(false)} // Handler to close delete dialog
					onConfirm={() => handleDeleteChat(currentChat.id)} // Handler to confirm delete action
					confirmButtonText="Delete" // Confirm button text - Delete
					confirmButtonColor="bg-red-600" // Confirm button background color - red
					confirmButtonBorderColor="border-red-600" // Confirm button border color - red
					confirmButtonIcon={IconTrash} // Confirm button icon - Trash icon
					showInput={false} // No input field in modal
				/>
			)}
		</>
	)
}

export default Sidebar
