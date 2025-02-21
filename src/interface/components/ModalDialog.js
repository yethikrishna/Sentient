import ShiningButton from "./ShiningButton" // Importing ShiningButton component
import React from "react"

/**
 * ModalDialog Component - A reusable modal dialog component.
 *
 * This component renders a modal dialog for various purposes like confirmations, prompts, or displaying information.
 * It includes options for a title, description, input field, confirm and cancel buttons, and customizable styling.
 *
 * @param {object} props - Component props.
 * @param {string} props.title - Title of the modal dialog.
 * @param {string} props.description - Description text within the modal dialog.
 * @param {string} props.inputPlaceholder - Placeholder text for the input field (if shown).
 * @param {string} props.inputValue - Value of the input field.
 * @param {function} props.onInputChange - Handler function for input field value changes.
 * @param {function} props.onCancel - Handler function for the cancel action.
 * @param {function} props.onConfirm - Handler function for the confirm action.
 * @param {string} props.confirmButtonText - Text to display on the confirm button, defaults to "Confirm".
 * @param {string} props.confirmButtonColor - Background color class for the confirm button, defaults to "bg-lightblue".
 * @param {string} props.confirmButtonBorderColor - Border color class for the confirm button, defaults to "bg-lightblue".
 * @param {React.ReactNode} props.confirmButtonIcon - Icon to display on the confirm button.
 * @param {boolean} props.showInput - Boolean to control visibility of the input field, defaults to false.
 * @param {React.ReactNode} props.extraContent - Extra content to display below the input field and description.
 * @param {boolean} props.cancelButton - Boolean to control visibility of the cancel button, defaults to true.
 * @returns {React.ReactNode} - The ModalDialog component UI.
 */
const ModalDialog = ({
	title, // Title of the modal dialog - title: string
	description = "", // Description text, default empty string - description: string
	inputPlaceholder = "", // Placeholder text for input field, default empty string - inputPlaceholder: string
	inputValue = "", // Input field value, default empty string - inputValue: string
	onInputChange, // Handler for input value changes - onInputChange: (value: string) => void
	onCancel, // Handler for cancel action - onCancel: () => void
	onConfirm, // Handler for confirm action - onConfirm: () => void
	confirmButtonText = "Confirm", // Text for confirm button, default "Confirm" - confirmButtonText: string
	confirmButtonColor = "bg-lightblue", // Color class for confirm button, default "bg-lightblue" - confirmButtonColor: string
	confirmButtonBorderColor = "bg-lightblue", // Border color class for confirm button, default "bg-lightblue" - confirmButtonBorderColor: string
	confirmButtonIcon, // Icon for confirm button - confirmButtonIcon: React.ReactNode
	showInput = false, // Show input field boolean, default false - showInput: boolean
	extraContent = null, // Extra content below input/description, default null - extraContent: React.ReactNode
	cancelButton = true // Show cancel button boolean, default true - cancelButton: boolean
}) => {
	return (
		<div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
			{/* Fixed overlay container: covers viewport, flex center alignment, semi-transparent black background, high z-index */}
			<div className="bg-matteblack rounded-lg p-6 shadow-lg space-y-4 w-1/4">
				{/* Dialog container: matte black background, rounded corners, padding, shadow, vertical spacing, quarter of viewport width */}
				<h3 className="text-xl text-white font-semibold">{title}</h3>
				{/* Dialog title: text size xl, white text color, semi-bold font weight */}
				{description && <p className="text-white">{description}</p>}
				{/* Description text: conditionally rendered if description prop is provided, white text color */}
				{showInput && (
					<input
						type="text"
						placeholder={inputPlaceholder} // Placeholder text from inputPlaceholder prop
						value={inputValue} // Input value from inputValue prop
						onChange={(e) => onInputChange(e.target.value)} // Calls onInputChange handler on input change
						className="w-full border border-gray-300 text-white rounded-lg p-2"
						// Input field styling: full width, border, gray-300 border color, rounded corners, padding
					/>
				)}
				{/* Extra content section: conditionally rendered if extraContent prop is provided, margin top for spacing */}
				{extraContent && <div className="mt-4">{extraContent}</div>}
				{/* Button container: flex layout, center alignment, horizontal spacing */}
				<div
					className={`flex items-center ${
						cancelButton ? "justify-between" : "justify-center"
					} px-10 space-x-2`}
				>
					{/* Conditional rendering of Cancel button based on cancelButton prop */}
					{cancelButton ? (
						<button
							onClick={onCancel} // Calls onCancel handler on button click
							className="p-1 w-1/2 h-[52px] text-gray-500 bg-gray-200 rounded-lg cursor-pointer"
							// Cancel button styling: padding, half width, fixed height, gray-500 text color, gray-200 background, rounded corners
						>
							Cancel
						</button>
					) : null}
					{/* ShiningButton component for Confirm action */}
					<ShiningButton
						onClick={onConfirm} // Calls onConfirm handler on button click
						bgColor={confirmButtonColor} // Background color from confirmButtonColor prop
						borderColor={confirmButtonBorderColor} // Border color from confirmButtonBorderColor prop
						icon={confirmButtonIcon} // Icon from confirmButtonIcon prop
						className={""} // No extra classNames
						borderClassName={"w-1/2"} // Border classNames, half width
					>
						{confirmButtonText}{" "}
						{/* Confirm button text from confirmButtonText prop */}
					</ShiningButton>
				</div>
			</div>
		</div>
	)
}

export default ModalDialog
