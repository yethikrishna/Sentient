import * as React from "react"
import { cn } from "@utils/cn"

const Textarea = React.forwardRef(({ className, ...props }, ref) => {
	return (
		<textarea
			className={cn(
				"flex min-h-[80px] w-full rounded-lg border border-neutral-700 bg-neutral-800/50 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sentient-blue focus-visible:ring-offset-2 focus-visible:ring-offset-black disabled:cursor-not-allowed disabled:opacity-50 custom-scrollbar",
				className
			)}
			ref={ref}
			{...props}
		/>
	)
})
Textarea.displayName = "Textarea"

export { Textarea }
