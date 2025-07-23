"use client"

import React from "react"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"

const ScheduleEditor = ({ schedule, setSchedule }) => {
	const handleTypeChange = (type) => {
		const baseSchedule = { ...schedule, type: type }
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
		<div className="bg-neutral-800/50 p-4 rounded-lg space-y-4 border border-neutral-700/80">
			<div className="flex items-center gap-2">
				{[
					{ label: "Run Once", value: "once" },
					{ label: "Recurring", value: "recurring" }
				].map(({ label, value }) => (
					<button
						key={value}
						type="button"
						onClick={() => handleTypeChange(value)}
						className={cn(
							"px-4 py-1.5 rounded-full text-sm font-medium",
							(schedule.type || "once") === value
								? "bg-blue-600 text-white"
								: "bg-neutral-700 hover:bg-neutral-600"
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
						value={
							schedule.run_at
								? new Date(schedule.run_at)
										.toISOString()
										.slice(0, 16)
								: ""
						}
						onChange={(e) =>
							setSchedule({ ...schedule, run_at: e.target.value })
						}
						className="w-full p-2 bg-neutral-700 border border-neutral-600 rounded-md focus:border-blue-500"
					/>
					<p className="text-xs text-gray-500 mt-1">
						If left blank, the task will be planned immediately.
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
							className="w-full p-2 bg-neutral-700 border border-neutral-600 rounded-md focus:border-blue-500"
						>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly</option>
						</select>
					</div>
					<div>
						<label
							className="text-xs text-gray-400 block mb-1"
							data-tooltip-id="schedule-tooltip"
							data-tooltip-content="Tasks are scheduled in Coordinated Universal Time (UTC) to ensure consistency across timezones."
						>
							Time (UTC)
						</label>
						<Tooltip
							place="top"
							id="schedule-tooltip"
							style={{ zIndex: 99999 }}
						/>
						<input
							type="time"
							value={schedule.time || "09:00"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									time: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-700 border border-neutral-600 rounded-md focus:border-blue-500"
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
										type="button"
										key={day}
										onClick={() => handleDayToggle(day)}
										className={cn(
											"px-3 py-1.5 rounded-full text-xs font-semibold",
											(schedule.days || []).includes(day)
												? "bg-blue-600 text-white"
												: "bg-neutral-700 hover:bg-neutral-600"
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
