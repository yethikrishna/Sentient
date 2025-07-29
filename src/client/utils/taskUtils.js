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
