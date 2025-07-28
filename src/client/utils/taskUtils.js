import {
	isToday,
	isTomorrow,
	isAfter,
	startOfDay,
	eachDayOfInterval,
	parseISO,
	getDay
} from "date-fns"

/**
 * Expands recurring tasks into individual instances within a given date range.
 * Also assigns a scheduled_date to all tasks for easier sorting and display.
 *
 * @param {Array} tasks - The raw list of tasks from the API.
 * @param {Date} startDate - The start of the date range.
 * @param {Date} endDate - The end of the date range.
 * @returns {Array} A new array of tasks with recurring tasks expanded.
 */
export function expandRecurringTasks(tasks, startDate, endDate) {
	const expandedTasks = []
	const today = startOfDay(new Date())
	const dayNames = [
		"Sunday",
		"Monday",
		"Tuesday",
		"Wednesday",
		"Thursday",
		"Friday",
		"Saturday"
	]

	const intervalDays = eachDayOfInterval({ start: startDate, end: endDate })

	tasks.forEach((task) => {
		if (task.schedule?.type === "recurring") {
			intervalDays.forEach((day) => {
				const dayOfWeek = dayNames[getDay(day)]
				let shouldRun = false

				if (task.schedule.frequency === "daily") {
					shouldRun = true
				} else if (
					task.schedule.frequency === "weekly" &&
					task.schedule.days?.includes(dayOfWeek)
				) {
					shouldRun = true
				}

				if (shouldRun) {
					expandedTasks.push({
						...task,
						// This is a virtual property for display purposes
						scheduled_date: day,
						// Add an ID to differentiate instances of the same recurring task
						instance_id: `${task.task_id}-${day.toISOString()}`
					})
				}
			})
		} else {
			// One-time tasks
			let scheduledDate = null
			if (task.schedule?.run_at) {
				scheduledDate = parseISO(task.schedule.run_at)
			} else {
				// Unscheduled tasks show up in "Today"
				scheduledDate = today
			}
			expandedTasks.push({
				...task,
				scheduled_date: scheduledDate,
				instance_id: task.task_id
			})
		}
	})

	return expandedTasks
}

/**
 * Groups tasks into 'today', 'tomorrow', and 'future' categories.
 *
 * @param {Array} tasks - A list of tasks, already expanded with `scheduled_date`.
 * @returns {Object} An object with keys `today`, `tomorrow`, `future`.
 */
export function groupTasksByDate(tasks) {
	const today = tasks.filter((task) => isToday(task.scheduled_date))
	const tomorrow = tasks.filter((task) => isTomorrow(task.scheduled_date))
	const future = tasks.filter(
		(task) =>
			isAfter(task.scheduled_date, new Date()) &&
			!isToday(task.scheduled_date) &&
			!isTomorrow(task.scheduled_date)
	)

	// Sort each group by priority (0=High, 1=Medium, 2=Low)
	const sortByPriority = (a, b) => (a.priority ?? 1) - (b.priority ?? 1)
	today.sort(sortByPriority)
	tomorrow.sort(sortByPriority)
	future.sort(sortByPriority)

	return { today, tomorrow, future }
}
