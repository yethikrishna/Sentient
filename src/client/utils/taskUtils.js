import {
	isToday,
	isTomorrow,
	isAfter,
	startOfDay,
	parseISO,
	getDay,
	addDays,
	isSameDay
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

/**
 * Gets the best display name for a task, handling legacy/generic names.
 * @param {object} task - The task object.
 * @returns {string} The display name for the task.
 */
export function getDisplayName(task) {
	if (!task) return "Untitled Task"

	// Use description if name is a generic placeholder
	if (task.name === "Proactively generated plan" && task.description) {
		return task.description
	}
	// Fallback to the original prompt from the first run if description is also generic/missing
	if (
		task.name === "Proactively generated plan" &&
		task.runs &&
		task.runs.length > 0 &&
		task.runs[0].prompt
	) {
		return task.runs[0].prompt
	}
	return task.name || "Untitled Task"
}

/**
 * Calculates the next run time for a recurring task.
 * @param {object} schedule - The task's schedule object.
 * @param {string} createdAt - The ISO string of when the task was created.
 * @param {Array} runs - The array of past runs for the task.
 * @returns {Date|null} The next run date object or null.
 */
export function calculateNextRun(schedule, createdAt, runs) {
	// FIX: Check that schedule.time is a string before trying to split it.
	// This handles cases where a recurring task is created without a specific time.
	if (
		!schedule ||
		schedule.type !== "recurring" ||
		typeof schedule.time !== "string"
	) {
		return null
	}

	const today = startOfDay(new Date())

	const lastRunTime =
		runs && runs.length > 0
			? runs.reduce((latest, run) => {
					// Also add a check for run.execution_start_time to be safe
					if (!run.execution_start_time) return latest
					const runTime = parseISO(run.execution_start_time)
					return runTime > latest ? runTime : latest
				}, new Date(0))
			: parseISO(createdAt || new Date(0)) // Gracefully handle missing createdAt

	let candidateDate = startOfDay(addDays(lastRunTime, 1)) // Start searching from the day after the last run

	const [hour, minute] = schedule.time.split(":").map(Number)

	const dayNames = [
		"Sunday",
		"Monday",
		"Tuesday",
		"Wednesday",
		"Thursday",
		"Friday",
		"Saturday"
	]
	const scheduledDays = schedule.days?.map((day) => dayNames.indexOf(day))

	if (
		schedule.frequency === "weekly" &&
		(!scheduledDays || scheduledDays.length === 0)
	)
		return null

	for (let i = 0; i < 365 * 2; i++) {
		const isScheduledDay =
			schedule.frequency === "daily" ||
			(schedule.frequency === "weekly" &&
				scheduledDays.includes(getDay(candidateDate)))
		if (
			isScheduledDay &&
			(isAfter(candidateDate, today) || isSameDay(candidateDate, today))
		) {
			candidateDate.setHours(hour, minute, 0, 0)
			return candidateDate
		}
		candidateDate = addDays(candidateDate, 1)
	}
	return null
}
