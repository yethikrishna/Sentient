"use client"

import React from "react"
import { cn } from "@utils/cn"

const ScheduleEditor = ({ schedule, setSchedule }) => {
	const handleTypeChange = (type) => {
		const baseSchedule = { ...schedule, type }
		if (type === "once") {
			delete baseSchedule.frequency
			delete baseSchedule.days
			delete baseSchedule.time
		} else {
			delete baseSchedule.run_at
		}
		setSchedule(baseSchedule)
	}

	const handleDayToggle = (day) => {
		const currentDays = schedule.days || []
		const newDays = currentDays.includes(day)
			? currentDays.filter((d) => d !== day)
			: [...currentDays, day]
		setSchedule({ ...schedule, days: newDays })
	}

	return (
		<div className="bg-neutral-800/50 p-4 rounded-lg space-y-4 border border-neutral-700/80 mt-2">
			<div className="flex items-center gap-2">
				{[
					{ label: "Run Once", value: "once" },
					{ label: "Recurring", value: "recurring" }
				].map(({ label, value }) => (
					<button
						key={value}
						onClick={() => handleTypeChange(value)}
						className={cn(
							(schedule.type || "once") === value
								? "bg-[var(--color-accent-blue)] text-white"
								: "bg-neutral-600 hover:bg-neutral-500",
							"px-4 py-1.5 rounded-full text-sm"
						)}
					>
						{label}
					</button>
				))}
			</div>

			{(schedule.type === "once" || !schedule.type) && (
				<div>
					<label className="text-xs text-gray-400 block mb-1">
						Run At (optional, local time)
					</label>
					<input
						type="datetime-local"
						value={schedule.run_at || ""}
						onChange={(e) =>
							setSchedule({ ...schedule, run_at: e.target.value })
						}
						className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
					/>
					<p className="text-xs text-gray-500 mt-1">
						If left blank, the task will run immediately after
						approval.
					</p>
				</div>
			)}

			{schedule.type === "recurring" && (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label className="text-xs text-gray-400 block mb-1">
							Frequency
						</label>
						<select
							value={schedule.frequency || "daily"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									frequency: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
						>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly</option>
						</select>
					</div>
					<div>
						<label
							className="text-xs text-gray-400 block mb-1"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Tasks are scheduled in Coordinated Universal Time (UTC) to ensure consistency across timezones."
						>
							Time (UTC)
						</label>
						<input
							type="time"
							value={schedule.time || "09:00"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									time: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
						/>
					</div>
					{schedule.frequency === "weekly" && (
						<div className="md:col-span-2">
							<label className="text-xs text-gray-400 block mb-2">
								Days
							</label>
							<div className="flex flex-wrap gap-2">
								{[
									"Monday",
									"Tuesday",
									"Wednesday",
									"Thursday",
									"Friday",
									"Saturday",
									"Sunday"
								].map((day) => (
									<button
										key={day}
										onClick={() => handleDayToggle(day)}
										className={cn(
											(schedule.days || []).includes(day)
												? "bg-[var(--color-accent-blue)] text-white"
												: "bg-neutral-600 hover:bg-neutral-500",
											"px-3 py-1.5 rounded-full text-xs font-semibold"
										)}
									>
										{day.substring(0, 3)}
									</button>
								))}
							</div>
						</div>
					)}
				</div>
			)}
		</div>
	)
}

export default ScheduleEditor
