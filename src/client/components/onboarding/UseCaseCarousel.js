import React from "react"
import {
	Carousel,
	CarouselContent,
	CarouselItem,
	CarouselNavigation,
	CarouselIndicator
} from "@components/ui/carousel"
import {
	IconSparkles,
	IconPlugConnected,
	IconHeart,
	IconBrain
} from "@tabler/icons-react"

const useCases = [
	{
		icon: <IconSparkles className="w-8 h-8 text-brand-orange" />,
		title: "Automate Your Tasks",
		description:
			"Describe a goal in natural language, and I'll create a plan and execute it for you across your connected apps."
	},
	{
		icon: <IconPlugConnected className="w-8 h-8 text-brand-orange" />,
		title: "Connect Your Apps",
		description:
			"Integrate with Google, Slack, Notion and more to bring all your information and capabilities together in one place."
	},
	{
		icon: <IconHeart className="w-8 h-8 text-brand-orange" />,
		title: "Personalized For You",
		description:
			"I learn about your preferences, context, and goals to provide truly personal and proactive assistance."
	},
	{
		icon: <IconBrain className="w-8 h-8 text-brand-orange" />,
		title: "Autopilot Mode",
		description:
			"I monitor your connected apps for important events and suggest actions you can take, helping you stay ahead."
	}
]

export function UseCaseCarousel() {
	return (
		<div className="relative w-full max-w-sm">
			<Carousel autoplay autoplayInterval={5000}>
				<CarouselContent>
					{useCases.map((useCase, index) => (
						<CarouselItem key={index} className="p-4">
							<div className="flex flex-col items-center justify-center text-center gap-4 p-6 h-80 rounded-2xl bg-neutral-800/60 border border-neutral-700/50 backdrop-blur-sm">
								{useCase.icon}
								<h3 className="text-2xl font-bold text-brand-white">
									{useCase.title}
								</h3>
								<p className="text-neutral-300">
									{useCase.description}
								</p>
							</div>
						</CarouselItem>
					))}
				</CarouselContent>
				<CarouselNavigation alwaysShow />
				<CarouselIndicator className="bottom-[-20px]" />
			</Carousel>
		</div>
	)
}
