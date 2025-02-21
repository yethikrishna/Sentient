/**
 * AppCard Component - Reusable card component for app integrations.
 *
 * This component is designed to display information about app integrations,
 * such as LinkedIn, Reddit, and Twitter. It includes a logo, name, description,
 * and a button for actions like "connect" or "disconnect". The card has a gradient
 * border and interactive hover effects.
 *
 * @param {object} props - Component props.
 * @param {string} props.logo - URL or path to the app logo image.
 * @param {string} props.name - Name of the application (e.g., LinkedIn, Reddit).
 * @param {string} props.description - Description of the app integration.
 * @param {function} props.onClick - Handler function to be called when the button is clicked.
 * @param {string} [props.action="connect"] - Text to display on the button, defaults to "connect".
 * @param {boolean} [props.loading=false] - Boolean to indicate if the button is in a loading state.
 * @param {boolean} [props.disabled=false] - Boolean to disable the button.
 * @param {string} [props.fromColor="#1E90FF"] - Starting color of the gradient border.
 * @param {string} [props.viaColor="#4682B4"] - Middle color of the gradient border.
 * @param {string} [props.toColor="#ADD8E6"] - Ending color of the gradient border.
 *
 * @returns {React.ReactNode} - The AppCard component UI.
 */

import React from "react"

const AppCard = ({
	logo, // URL or path to the app logo image - logo: string
	name, // Name of the application (e.g., LinkedIn, Reddit) - name: string
	description, // Description of the app integration - description: string
	onClick, // Handler function for button click - onClick: () => void
	action = "connect", // Text to display on the button, defaults to "connect" - action: string
	loading = false, // Boolean to indicate loading state, defaults to false - loading: boolean
	disabled = false, // Boolean to disable the button, defaults to false - disabled: boolean
	fromColor = "#1E90FF", // Starting color for gradient border, defaults to light blue - fromColor: string
	viaColor = "#4682B4", // Middle color for gradient border, defaults to steel blue - viaColor: string
	toColor = "#ADD8E6" // Ending color for gradient border, defaults to light steel blue - toColor: string
}) => {
	return (
		<div
			className="rounded-3xl w-1/3 bg-linear-to-r p-0.5 hover:shadow-glow hover:brightness-150"
			// Base styles for the card: rounded corners, width, gradient background, padding, hover effects for shadow and brightness
			style={{
				transition: "box-shadow 0.5s ease, filter 0.5s ease", // Smooth transition for hover effects
				backgroundImage: `linear-gradient(to right, ${fromColor}, ${viaColor}, ${toColor})` // Dynamic gradient background
			}}
		>
			<div className="flex flex-col items-center justify-center bg-gray-800 rounded-3xl p-6 shadow-lg">
				{/* Inner container for card content: flex column layout, center alignment, dark background, rounded corners, padding, shadow */}
				<img
					src={logo}
					alt={`${name} Logo`}
					className="w-16 h-16 mb-4"
				/>
				{/* Logo image: dynamic src and alt attributes, fixed width and height, margin at bottom */}
				<h2 className="text-white text-2xl mb-2">{name}</h2>
				{/* App name: white text color, text size 2xl, margin at bottom */}
				<p className="text-gray-400 text-center mb-4">{description}</p>
				{/* Description text: gray-400 text color, centered text alignment, margin at bottom */}
				<button
					className={`rounded-full text-white font-bold py-2 px-4 transition ${
						disabled
							? "opacity-50 cursor-not-allowed"
							: "gradient-bg cursor-pointer" // Dynamic classes: opacity and cursor for disabled state, gradient-bg for enabled
					}`}
					onClick={onClick} // Calls the onClick handler passed as prop
					disabled={disabled} // Disables the button based on the disabled prop
				>
					{/* Button element: rounded full corners, white text color, bold font, padding, transition for effects */}
					{
						action === "connect"
							? loading
								? "Connecting..." // Display "Connecting..." if loading is true and action is "connect"
								: "Connect" // Display "Connect" if loading is false and action is "connect"
							: action === "disconnect"
								? loading
									? "Disconnecting..." // Display "Disconnecting..." if loading is true and action is "disconnect"
									: "Disconnect" // Display "Disconnect" if loading is false and action is "disconnect"
								: action // Display the action prop value directly if action is neither "connect" nor "disconnect"
					}
				</button>
			</div>
		</div>
	)
}

export default AppCard
