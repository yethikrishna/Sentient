"use client"
import React from "react"
import { motion } from "framer-motion"

const ProgressBar = ({ score, totalQuestions }) => {
	const progress =
		totalQuestions > 0 ? (score / (totalQuestions * 10)) * 100 : 0

	return (
		<div className="w-full max-w-3xl mx-auto px-4">
			<div className="w-full bg-brand-gray h-2 overflow-hidden">
				<motion.div
					className="bg-brand-orange h-full"
					initial={{ width: "0%" }}
					animate={{ width: `${progress}%` }}
					transition={{ duration: 0.5, ease: "easeInOut" }}
				/>
			</div>
		</div>
	)
}

export default ProgressBar
