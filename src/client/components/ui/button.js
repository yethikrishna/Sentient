import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"

import { cn } from "@utils/cn"

const buttonVariants = cva(
	"inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium ring-offset-black transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sentient-blue focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
	{
		variants: {
			variant: {
				default:
					"bg-sentient-blue text-white hover:bg-sentient-blue-dark",
				destructive: "bg-red-600 text-white hover:bg-red-500",
				outline:
					"border border-neutral-700 bg-transparent hover:bg-neutral-800 hover:text-white",
				secondary: "bg-neutral-800 text-white hover:bg-neutral-700",
				ghost: "hover:bg-neutral-800 hover:text-white",
				link: "text-white underline-offset-4 hover:underline"
			},
			size: {
				default: "h-10 px-4 py-2",
				sm: "h-9 rounded-md px-3",
				lg: "h-11 rounded-md px-8",
				icon: "h-10 w-10"
			}
		},
		defaultVariants: {
			variant: "default",
			size: "default"
		}
	}
)

const Button = React.forwardRef(
	({ className, variant, size, asChild = false, ...props }, ref) => {
		const Comp = asChild ? Slot : "button"
		return (
			<Comp
				className={cn(buttonVariants({ variant, size, className }))}
				ref={ref}
				{...props}
			/>
		)
	}
)
Button.displayName = "Button"

export { Button, buttonVariants }
