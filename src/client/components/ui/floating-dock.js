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

export const FloatingDock = ({ items, desktopClassName, mobileClassName }) => {
	return (
		<>
			<FloatingDockDesktop items={items} className={desktopClassName} />
			<FloatingDockMobile items={items} className={mobileClassName} />
		</>
	)
}

const FloatingDockMobile = ({ items, className }) => {
	const [open, setOpen] = useState(false)
	return (
		<div
			className={cn(
				"fixed top-1/2 left-4 -translate-y-1/2 block md:hidden z-50",
				className
			)}
		>
			<AnimatePresence>
				{open && (
					<motion.div
						layoutId="nav-mobile"
						className="absolute left-full ml-2 flex flex-col gap-2"
						initial={{ opacity: 0, x: -10 }}
						animate={{ opacity: 1, x: 0 }}
						exit={{ opacity: 0, x: -10 }}
					>
						{items.map((item, idx) => (
							<motion.div
								key={item.title}
								initial={{ opacity: 0, x: -10 }}
								animate={{
									opacity: 1,
									x: 0,
									transition: { delay: idx * 0.05 }
								}}
								exit={{
									opacity: 0,
									x: -10,
									transition: {
										delay: (items.length - 1 - idx) * 0.05
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
									className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-50 dark:bg-neutral-900"
								>
									<div className="h-5 w-5">{item.icon}</div>
								</a>
							</motion.div>
						))}
					</motion.div>
				)}
			</AnimatePresence>
			<button
				onClick={() => setOpen(!open)}
				className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-50 dark:bg-neutral-800"
			>
				<IconLayoutNavbarCollapse className="h-6 w-6 text-neutral-500 dark:text-neutral-400" />
			</button>
		</div>
	)
}

const FloatingDockDesktop = ({ items, className }) => {
	let mouseY = useMotionValue(Infinity)
	return (
		<motion.div
			onMouseMove={(e) => mouseY.set(e.pageY)}
			onMouseLeave={() => mouseY.set(Infinity)}
			className={cn(
				"fixed top-1/2 left-4 -translate-y-1/2 hidden flex-col items-center gap-4 rounded-2xl bg-gray-50/50 dark:bg-neutral-900/50 backdrop-blur-md p-4 md:flex z-50",
				className
			)}
		>
			{items.map((item) => (
				<IconContainer mouseY={mouseY} key={item.title} {...item} />
			))}
		</motion.div>
	)
}

function IconContainer({ mouseY, title, icon, href, onClick }) {
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
				className="relative flex aspect-square items-center justify-center rounded-full bg-gray-200 dark:bg-neutral-800"
			>
				<AnimatePresence>
					{hovered && (
						<motion.div
							initial={{ opacity: 0, x: 10, y: "-50%" }}
							animate={{ opacity: 1, x: 0, y: "-50%" }}
							exit={{ opacity: 0, x: 5, y: "-50%" }}
							className="absolute left-full ml-4 top-1/2 w-fit rounded-md border border-gray-200 bg-gray-100 px-2 py-0.5 text-xs whitespace-pre text-neutral-700 dark:border-neutral-900 dark:bg-neutral-800 dark:text-white"
						>
							{title}
						</motion.div>
					)}
				</AnimatePresence>
				<motion.div
					style={{ width: widthIcon, height: heightIcon }}
					className="flex items-center justify-center"
				>
					{icon}
				</motion.div>
			</motion.div>
		</a>
	)
}
