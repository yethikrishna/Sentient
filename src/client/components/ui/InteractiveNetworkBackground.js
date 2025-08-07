// src/client/components/ui/InteractiveNetworkBackground.js
"use client"
import React, { useRef, useEffect } from "react"
import { cn } from "@utils/cn"

const InteractiveNetworkBackground = ({ className }) => {
	const canvasRef = useRef(null)

	useEffect(() => {
		const canvas = canvasRef.current
		if (!canvas) return

		const ctx = canvas.getContext("2d")
		let animationFrameId
		let time = 0

		// Disable on mobile for performance
		if (window.innerWidth < 768) {
			return
		}

		const setup = () => {
			canvas.width = window.innerWidth
			canvas.height = window.innerHeight
		}

		const particles = []
		const particleCount = 150
		const connectionDistance = 150

		class Particle {
			constructor() {
				this.x = Math.random() * canvas.width
				this.y = Math.random() * canvas.height
				this.vx = (Math.random() - 0.5) * 0.5
				this.vy = (Math.random() - 0.5) * 0.5
				this.radius = 1.5
				this.pulseOffset = Math.random() * Math.PI * 2
			}

			update() {
				if (this.x < 0 || this.x > canvas.width) this.vx *= -1
				if (this.y < 0 || this.y > canvas.height) this.vy *= -1
				this.x += this.vx
				this.y += this.vy
			}

			draw() {
				const pulseRadius =
					this.radius + Math.sin(time * 0.05 + this.pulseOffset) * 0.5
				ctx.beginPath()
				ctx.arc(this.x, this.y, pulseRadius, 0, Math.PI * 2)
				ctx.fillStyle = "rgba(241, 162, 29, 0.5)"
				ctx.fill()
			}
		}

		const init = () => {
			particles.length = 0
			for (let i = 0; i < particleCount; i++) {
				particles.push(new Particle())
			}
		}

		const animate = () => {
			time++
			ctx.clearRect(0, 0, canvas.width, canvas.height)
			particles.forEach((p) => {
				p.update()
				p.draw()
			})
			connect()
			animationFrameId = requestAnimationFrame(animate)
		}

		const connect = () => {
			for (let i = 0; i < particles.length; i++) {
				for (let j = i + 1; j < particles.length; j++) {
					const distance = Math.sqrt(
						Math.pow(particles[i].x - particles[j].x, 2) +
							Math.pow(particles[i].y - particles[j].y, 2)
					)
					if (distance < connectionDistance) {
						const opacity = 1 - distance / connectionDistance
						ctx.strokeStyle = `rgba(241, 162, 29, ${opacity})`
						ctx.lineWidth = 0.7
						ctx.beginPath()
						ctx.moveTo(particles[i].x, particles[i].y)
						ctx.lineTo(particles[j].x, particles[j].y)
						ctx.stroke()
					}
				}
			}
		}

		const handleResize = () => {
			setup()
			init()
		}

		setup()
		init()
		animate()

		window.addEventListener("resize", handleResize)

		return () => {
			window.removeEventListener("resize", handleResize)
			cancelAnimationFrame(animationFrameId)
		}
	}, [])

	return (
		<canvas
			ref={canvasRef}
			className={cn("absolute inset-0 z-[-1] opacity-30", className)}
			aria-hidden="true"
		/>
	)
}

export default InteractiveNetworkBackground
