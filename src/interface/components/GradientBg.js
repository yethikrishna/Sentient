"use client"
import { useEffect, useRef, useState } from "react" // Importing React hooks: useEffect, useRef, useState
import { clsx } from "clsx" // Importing clsx for conditionally joining class names
import { twMerge } from "tailwind-merge" // Importing twMerge for merging Tailwind CSS class names
import React from "react"

/**
 * Utility function to conditionally merge and apply class names.
 * Combines class names using clsx and then merges Tailwind CSS class names using twMerge.
 *
 * @param {...any} inputs - Class names to be merged and applied.
 * @returns {string} - Merged and optimized class names string.
 */
const cn = (...inputs) => {
	return twMerge(clsx(inputs)) // Merges class names using twMerge after conditional joining with clsx
}

/**
 * BackgroundGradientAnimation Component - Animates a gradient background with interactive pointer effects.
 *
 * This component creates an animated gradient background with multiple layers of radial gradients
 * that subtly shift and blend to produce a dynamic, moving background effect. It also features
 * an interactive layer that follows the mouse cursor, enhancing the sense of depth and interactivity.
 *
 * @param {object} props - Component props.
 * @param {string} props.gradientBackgroundStart - Starting color of the linear gradient background.
 * @param {string} props.gradientBackgroundEnd - Ending color of the linear gradient background.
 * @param {string} props.firstColor - Color for the first radial gradient layer (RGBA format string).
 * @param {string} props.secondColor - Color for the second radial gradient layer (RGBA format string).
 * @param {string} props.thirdColor - Color for the third radial gradient layer (RGBA format string).
 * @param {string} props.pointerColor - Color for the interactive pointer gradient layer (RGBA format string).
 * @param {string} props.size - Size of the radial gradients (e.g., "80%", "500px").
 * @param {string} props.blendingValue - Blending mode for the gradient layers (e.g., "hard-light", "soft-light").
 * @param {React.ReactNode} props.children - Content to be rendered on top of the gradient background.
 * @param {string} props.className - Optional CSS class names to apply to the content container.
 * @param {string} props.interactive - Boolean to enable or disable the interactive pointer layer.
 * @param {string} props.containerClassName - Optional CSS class names to apply to the background container.
 * @returns {React.ReactNode} - The BackgroundGradientAnimation component UI.
 */
export const BackgroundGradientAnimation = ({
	gradientBackgroundStart = "rgb(33, 33, 33)", // Default starting color for gradient background - gradientBackgroundStart: string
	gradientBackgroundEnd = "rgb(33, 33, 33)", // Default ending color for gradient background - gradientBackgroundEnd: string
	firstColor = "0, 92, 254", // Default color for the first gradient layer - firstColor: string (RGBA format)
	secondColor = "0, 178, 254", // Default color for the second gradient layer - secondColor: string (RGBA format)
	thirdColor = "0, 92, 254", // Default color for the third gradient layer - thirdColor: string (RGBA format)
	pointerColor = "0, 178, 254", // Default color for the pointer gradient layer - pointerColor: string (RGBA format)
	size = "80%", // Default size for the radial gradients - size: string (CSS size unit)
	blendingValue = "hard-light", // Default blending mode for gradients - blendingValue: string (CSS blend mode value)
	children, // Content to be rendered on top of the gradient background - children: React.ReactNode
	className, // Optional class names for content container - className: string
	interactive = true, // Boolean to enable/disable interactive pointer layer - interactive: boolean
	containerClassName // Optional class names for background container - containerClassName: string
}) => {
	const interactiveRef = useRef(null) // useRef for the interactive gradient layer - interactiveRef: React.RefObject<HTMLDivElement>

	// State variables for current and target X and Y coordinates for smooth animation
	const [curX, setCurX] = useState(960) // Current X coordinate, initialized to 960 - curX: number
	const [curY, setCurY] = useState(540) // Current Y coordinate, initialized to 540 - curY: number
	const [tgX, setTgX] = useState(0) // Target X coordinate, initialized to 0 - tgX: number
	const [tgY, setTgY] = useState(0) // Target Y coordinate, initialized to 0 - tgY: number

	/**
	 * useEffect hook to set CSS variables on document body for gradient styling.
	 *
	 * Sets various CSS custom properties (variables) on the document body element to control
	 * the gradient background colors, pointer color, size, and blending value. These variables
	 * are then used in the inline styles of child elements to dynamically style the gradients.
	 */
	useEffect(() => {
		document.body.style.setProperty(
			"--gradient-background-start",
			gradientBackgroundStart
		) // Set CSS variable for gradient start color
		document.body.style.setProperty(
			"--gradient-background-end",
			gradientBackgroundEnd
		) // Set CSS variable for gradient end color
		document.body.style.setProperty("--first-color", firstColor) // Set CSS variable for first gradient color
		document.body.style.setProperty("--second-color", secondColor) // Set CSS variable for second gradient color
		document.body.style.setProperty("--third-color", thirdColor) // Set CSS variable for third gradient color
		document.body.style.setProperty("--pointer-color", pointerColor) // Set CSS variable for pointer gradient color
		document.body.style.setProperty("--size", size) // Set CSS variable for gradient size
		document.body.style.setProperty("--blending-value", blendingValue) // Set CSS variable for blending mode
	}, []) // Empty dependency array ensures this effect runs only once on mount

	/**
	 * useEffect hook to animate the interactive gradient layer to follow the mouse smoothly.
	 *
	 * Uses requestAnimationFrame for smooth animation of the interactive gradient layer.
	 * It updates the current X and Y coordinates (`curX`, `curY`) to gradually move towards the target
	 * coordinates (`tgX`, `tgY`), creating a smooth following effect. The transform style of the
	 * `interactiveRef.current` element is updated in each animation frame.
	 */
	useEffect(() => {
		/**
		 * Animation function to smoothly move the interactive gradient towards the target position.
		 *
		 * This function is called in each frame of the animation. It calculates the difference between
		 * the current and target positions and updates the current position to move closer to the target,
		 * creating a smooth animation effect. It then applies a CSS transform to the interactive element
		 * to reflect the updated position.
		 * @function move
		 * @returns {void}
		 */
		function move() {
			if (!interactiveRef.current) {
				return // If interactiveRef is not yet attached to a DOM element, return early
			}
			setCurX(curX + (tgX - curX) / 20) // Smoothly update curX towards tgX
			setCurY(curY + (tgY - curY) / 20) // Smoothly update curY towards tgY
			interactiveRef.current.style.transform = `translate(${Math.round(
				curX
			)}px, ${Math.round(curY)}px)` // Apply transform to move interactive element
		}

		// Animation frame requested in useEffect to run animation smoothly
		requestAnimationFrame(move)
	}, [tgX, tgY]) // Effect dependencies: tgX, tgY - effect runs when target coordinates change

	/**
	 * Handles mouse move events to update the target coordinates for the interactive gradient.
	 *
	 * When the mouse moves over the interactive area, this function calculates the mouse position
	 * relative to the interactive element and updates the target X and Y coordinates (`tgX`, `tgY`)
	 * to make the interactive gradient follow the mouse.
	 *
	 * @function handleMouseMove
	 * @param {MouseEvent} event - The mousemove event object.
	 * @param {HTMLElement} event.currentTarget - The element that the event listener is attached to (interactiveRef.current).
	 * @returns {void}
	 */
	const handleMouseMove = (event) => {
		if (interactiveRef.current) {
			const rect = interactiveRef.current.getBoundingClientRect() // Get bounding rectangle of the interactive element
			setTgX(event.clientX - rect.left) // Set target X coordinate relative to the interactive element
			setTgY(event.clientY - rect.top) // Set target Y coordinate relative to the interactive element
		}
	}

	// State to detect if the browser is Safari - isSafari: boolean
	const [isSafari, setIsSafari] = useState(false)
	/**
	 * useEffect hook to detect if the browser is Safari.
	 *
	 * Sets the `isSafari` state based on userAgent string to apply browser-specific styles or workarounds, if needed.
	 */
	useEffect(() => {
		setIsSafari(/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) // Detect Safari browser using userAgent string
	}, []) // Empty dependency array ensures this effect runs only once on mount

	return (
		<div
			className={cn(
				"relative overflow-hidden top-0 left-0 bg-[linear-gradient(40deg,var(--gradient-background-start),var(--gradient-background-end))]",
				// Base container classes: relative positioning, overflow hidden, top and left position 0, linear gradient background from CSS vars, dynamic containerClassName
				containerClassName
			)}
			style={{ zIndex: 0, opacity: 0.5 }}
		>
			{/* SVG filter definition for blur effect (hidden) */}
			<svg className="hidden">
				<defs>
					<filter id="blurMe">
						{/* Gaussian blur filter */}
						<feGaussianBlur
							in="SourceGraphic"
							stdDeviation="10"
							result="blur-sm"
						/>
						{/* Color matrix to adjust blur and create "gooey" effect */}
						<feColorMatrix
							in="blur-sm"
							mode="matrix"
							values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -8"
							result="goo"
						/>
						{/* Blend filter to combine original graphic with blurred and adjusted version */}
						<feBlend in="SourceGraphic" in2="goo" />
					</filter>
				</defs>
			</svg>
			{/* Container for children, rendered above the gradient background, dynamic className */}
			<div className={cn("", className)}>{children}</div>
			{/* Container for gradient layers with blur effect */}
			<div
				className={cn(
					"gradients-container h-full w-full blur-lg", // Base classes: full height and width, blur effect
					isSafari ? "blur-2xl" : "[filter:url(#blurMe)_blur(40px)]" // Apply different blur effect for Safari and other browsers
				)}
			>
				{/* First gradient layer */}
				<div
					className={cn(
						`absolute [background:radial-gradient(circle_at_center,_var(--first-color)_0,_var(--first-color)_50%)_no-repeat]`,
						// Absolute positioning, radial gradient background from CSS var, no-repeat
						`[mix-blend-mode:var(--blending-value)] w-[var(--size)] h-[var(--size)] top-[calc(50%-var(--size)/2)] left-[calc(50%-var(--size)/2)]`,
						// Blending mode from CSS var, width and height from CSS var, positioning to center gradient
						`[transform-origin:center_center]`, // Transform origin for rotation/scaling
						`animate-first`, // Animation class for the first layer
						`opacity-100` // Opacity set to 100%
					)}
				></div>
				{/* Second gradient layer */}
				<div
					className={cn(
						`absolute [background:radial-gradient(circle_at_center,_rgba(var(--second-color),_0.8)_0,_rgba(var(--second-color),_0)_50%)_no-repeat]`,
						// Absolute positioning, radial gradient background with opacity from CSS var, no-repeat
						`[mix-blend-mode:var(--blending-value)] w-[var(--size)] h-[var(--size)] top-[calc(50%-var(--size)/2)] left-[calc(50%-var(--size)/2)]`,
						// Blending mode from CSS var, width and height from CSS var, positioning to center gradient
						`[transform-origin:calc(50%-400px)]`, // Transform origin shifted for parallax effect
						`animate-second`, // Animation class for the second layer
						`opacity-100` // Opacity set to 100%
					)}
				></div>
				{/* Third gradient layer */}
				<div
					className={cn(
						`absolute [background:radial-gradient(circle_at_center,_rgba(var(--third-color),_0.8)_0,_rgba(var(--third-color),_0)_50%)_no-repeat]`,
						// Absolute positioning, radial gradient background with opacity from CSS var, no-repeat
						`[mix-blend-mode:var(--blending-value)] w-[var(--size)] h-[var(--size)] top-[calc(50%-var(--size)/2)] left-[calc(50%-var(--size)/2)]`,
						// Blending mode from CSS var, width and height from CSS var, positioning to center gradient
						`[transform-origin:calc(50%+400px)]`, // Transform origin shifted for parallax effect
						`animate-third`, // Animation class for the third layer
						`opacity-100` // Opacity set to 100%
					)}
				></div>
				{/* Fourth gradient layer */}
				<div
					className={cn(
						`absolute [background:radial-gradient(circle_at_center,_rgba(var(--fourth-color),_0.8)_0,_rgba(var(--fourth-color),_0)_50%)_no-repeat]`,
						// Absolute positioning, radial gradient background with opacity from CSS var, no-repeat
						`[mix-blend-mode:var(--blending-value)] w-[var(--size)] h-[var(--size)] top-[calc(50%-var(--size)/2)] left-[calc(50%-var(--size)/2)]`,
						// Blending mode from CSS var, width and height from CSS var, positioning to center gradient
						`[transform-origin:calc(50%-200px)]`, // Transform origin shifted for parallax effect
						`animate-fourth`, // Animation class for the fourth layer
						`opacity-70` // Opacity set to 70%
					)}
				></div>
				{/* Fifth gradient layer */}
				<div
					className={cn(
						`absolute [background:radial-gradient(circle_at_center,_rgba(var(--fifth-color),_0.8)_0,_rgba(var(--fifth-color),_0)_50%)_no-repeat]`,
						// Absolute positioning, radial gradient background with opacity from CSS var, no-repeat
						`[mix-blend-mode:var(--blending-value)] w-[var(--size)] h-[var(--size)] top-[calc(50%-var(--size)/2)] left-[calc(50%-var(--size)/2)]`,
						// Blending mode from CSS var, width and height from CSS var, positioning to center gradient
						`[transform-origin:calc(50%-800px)_calc(50%+800px)]`, // Transform origin shifted and offset for parallax effect
						`animate-fifth`, // Animation class for the fifth layer
						`opacity-100` // Opacity set to 100%
					)}
				></div>

				{/* Interactive gradient layer, conditionally rendered based on 'interactive' prop */}
				{interactive && (
					<div
						ref={interactiveRef} // Attach interactiveRef to this div
						onMouseMove={handleMouseMove} // Call handleMouseMove function on mouse move
						className={cn(
							`absolute [background:radial-gradient(circle_at_center,_rgba(var(--pointer-color),_0.8)_0,_rgba(var(--pointer-color),_0)_50%)_no-repeat]`,
							// Absolute positioning, radial gradient background with pointer color from CSS var, no-repeat
							`[mix-blend-mode:var(--blending-value)] w-full h-full -top-1/2 -left-1/2`,
							// Blending mode from CSS var, full width and height, negative top and left to center gradient
							`opacity-70` // Opacity set to 70%
						)}
					></div>
				)}
			</div>
		</div>
	)
}
