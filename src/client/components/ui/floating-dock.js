import { cn } from "@utils/cn"
import { IconLayoutNavbarCollapse } from "@tabler/icons-react"
import {
	AnimatePresence,
	motion,
	useMotionValue,
	useSpring,
	useTransform
} from "framer-motion"

import { useRef, useState } from "react"
import { usePathname } from "next/navigation"
import React from "react"

export const FloatingDock = ({ items, desktopClassName, mobileClassName }) => {
	const pathname = usePathname()
	return (
		<>
			<FloatingDockDesktop
				items={items}
				className={desktopClassName}
				pathname={pathname}
			/>
			<FloatingDockMobile
				items={items}
				className={mobileClassName}
				pathname={pathname}
			/>
		</>
	)
}

const FloatingDockMobile = ({ items, className, pathname }) => {
	const [open, setOpen] = useState(false)
	return (
		<div
			className={cn(
				"fixed bottom-4 left-4 block md:hidden z-50 select-none",
				className
			)}
		>
			<AnimatePresence>
				{open && (
					<motion.div
						layoutId="nav-mobile"
						className="absolute bottom-full mb-3 flex flex-col gap-2"
						initial={{ opacity: 0, y: 10 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0, y: 10 }}
					>
						{items.map((item, idx) => {
							const isActive = item.href === pathname
							const newIcon = React.cloneElement(item.icon, {
								className: cn(
									item.icon.props.className,
									isActive && "text-white"
								)
							})
							return (
								<motion.div
									key={item.title}
									initial={{ opacity: 0, y: 10 }}
									animate={{
										// eslint-disable-line
										opacity: 1,
										y: 0,
										transition: { delay: idx * 0.05 }
									}}
									exit={{
										opacity: 0,
										y: 10,
										transition: {
											delay:
												(items.length - 1 - idx) * 0.05
										}
									}}
								>
									<a
										href={item.href}
										onClick={(e) => {
											if (item.onClick) {
												e.preventDefault()
												item.onClick()
											}
										}}
										key={item.title}
										className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] shadow-lg backdrop-blur-sm hover:bg-[var(--color-primary-surface-elevated)] transition-all duration-200"
									>
										<div className="h-5 w-5">{newIcon}</div>
									</a>
								</motion.div>
							)
						})}
					</motion.div>
				)}
			</AnimatePresence>
			<button
				onClick={() => setOpen(!open)}
				className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] shadow-lg backdrop-blur-sm hover:bg-[var(--color-primary-surface-elevated)] transition-all duration-200"
			>
				<IconLayoutNavbarCollapse className="h-5 w-5 text-[var(--color-text-primary)]" />
			</button>
		</div>
	)
}

const FloatingDockDesktop = ({ items, className, pathname }) => {
	let mouseY = useMotionValue(Infinity)
	return (
		<motion.div
			onMouseMove={(e) => mouseY.set(e.pageY)}
			onMouseLeave={() => mouseY.set(Infinity)}
			className={cn(
				"fixed top-1/2 left-4 -translate-y-1/2 hidden flex-col items-center gap-3 rounded-2xl bg-[var(--color-primary-surface)]/80 backdrop-blur-xl border border-[var(--color-primary-surface-elevated)] shadow-xl p-3 md:flex z-50 select-none",
				className
			)}
		>
			{items.map((item) => (
				<IconContainer
					mouseY={mouseY}
					key={item.title}
					{...item}
					pathname={pathname}
				/>
			))}
		</motion.div>
	)
}

function IconContainer({ mouseY, title, icon, href, onClick, pathname }) {
	let ref = useRef(null)

	let distance = useTransform(mouseY, (val) => {
		let bounds = ref.current?.getBoundingClientRect() ?? { y: 0, height: 0 }
		return val - bounds.y - bounds.height / 2
	})

	let widthTransform = useTransform(distance, [-150, 0, 150], [40, 80, 40])
	let heightTransform = useTransform(distance, [-150, 0, 150], [40, 80, 40])

	let widthTransformIcon = useTransform(
		distance,
		[-150, 0, 150],
		[20, 40, 20]
	)
	let heightTransformIcon = useTransform(
		distance,
		[-150, 0, 150],
		[20, 40, 20]
	)

	let width = useSpring(widthTransform, {
		mass: 0.1,
		stiffness: 150,
		damping: 12
	})
	let height = useSpring(heightTransform, {
		mass: 0.1,
		stiffness: 150,
		damping: 12
	})

	let widthIcon = useSpring(widthTransformIcon, {
		mass: 0.1,
		stiffness: 150,
		damping: 12
	})
	let heightIcon = useSpring(heightTransformIcon, {
		mass: 0.1,
		stiffness: 150,
		damping: 12
	})

	const [hovered, setHovered] = useState(false)
	const isActive = href === pathname

	const newIcon = React.cloneElement(icon, {
		className: cn(icon.props.className, isActive && "text-white")
	})

	return (
		<a
			href={href}
			onClick={(e) => {
				if (onClick) {
					e.preventDefault()
					onClick()
				}
			}}
		>
			<motion.div
				ref={ref}
				style={{ width, height }}
				onMouseEnter={() => setHovered(true)}
				onMouseLeave={() => setHovered(false)}
				className={cn(
					"relative flex aspect-square items-center justify-center rounded-full bg-[var(--color-primary-surface-elevated)] transition-all duration-200 border border-[var(--color-primary-surface-elevated)] shadow-md hover:shadow-lg",
					isActive
						? "bg-[var(--color-accent-blue)]"
						: "hover:bg-[var(--color-accent-blue)]/20"
				)}
			>
				<AnimatePresence>
					{hovered && (
						<motion.div
							initial={{ opacity: 0, x: 10, y: "-50%" }}
							animate={{ opacity: 1, x: 0, y: "-50%" }}
							exit={{ opacity: 0, x: 5, y: "-50%" }}
							className="absolute left-full ml-4 top-1/2 w-fit rounded-lg border border-[var(--color-primary-surface-elevated)] bg-[var(--color-primary-surface)] backdrop-blur-sm px-3 py-1.5 text-sm whitespace-pre text-[var(--color-text-primary)] shadow-lg z-10"
						>
							{title}
						</motion.div>
					)}
				</AnimatePresence>
				<motion.div
					style={{ width: widthIcon, height: heightIcon }}
					className="flex items-center justify-center"
				>
					{newIcon}
				</motion.div>
			</motion.div>
		</a>
	)
}
