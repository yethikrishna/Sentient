import { useEffect } from "react"
import Lenis from "lenis"

/**
 * A custom React hook to apply Lenis smooth scrolling to a specific element.
 *
 * @param {React.RefObject<HTMLElement>} ref - A React ref attached to the scrollable container element.
 */
export function useSmoothScroll(ref) {
	useEffect(() => {
		if (!ref.current) return

		// Initialize Lenis on the specific element
		const lenis = new Lenis({
			wrapper: ref.current, // The element that has the overflow
			content: ref.current, // The element that is being scrolled
			duration: 1.2,
			easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
			smoothTouch: true
		})

		let animationFrameId

		function raf(time) {
			lenis.raf(time)
			animationFrameId = requestAnimationFrame(raf)
		}

		animationFrameId = requestAnimationFrame(raf)

		// Cleanup function to destroy the Lenis instance when the component unmounts
		return () => {
			cancelAnimationFrame(animationFrameId)
			lenis.destroy()
		}
	}, [ref]) // Rerun effect if the ref changes
}
