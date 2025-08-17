import { useContext } from "react"
import { PlanContext } from "@components/LayoutWrapper"

/**
 * Custom hook to easily access the user's current pricing plan.
 * @returns {{plan: 'free' | 'pro', isPro: boolean, isLoading: boolean}}
 */
export const usePlan = () => {
	return useContext(PlanContext)
}
