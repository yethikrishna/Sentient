"use client"
import React, { useState, useEffect, useCallback } from "react"
import Sidebar from "@components/Sidebar"
import { IconMicrophone, IconInfoCircle } from "@tabler/icons-react"
import toast from "react-hot-toast"

const VoicePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user details")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
		}
	}, [])

	useEffect(() => {
		fetchUserDetails()
	}, [fetchUserDetails])

	return (
		<div className="h-screen bg-matteblack flex relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-grow flex flex-col h-full bg-matteblack text-white relative overflow-hidden p-6 md:p-10 items-center justify-center">
				<div className="text-center p-8 bg-neutral-900/50 rounded-lg border border-neutral-700 shadow-xl max-w-2xl">
					<IconMicrophone className="w-20 h-20 text-lightblue mx-auto mb-6" />
					<h1 className="font-Poppins text-white text-4xl font-light mb-4">
						Voice Features Coming Soon!
					</h1>
					<p className="text-gray-300 mb-2 text-lg">
						You're currently using a beta version of Sentient.
					</p>
					<p className="text-gray-400 text-md mb-6">
						We're hard at work developing a seamless and intuitive
						voice experience. Exciting voice interaction
						capabilities will be added to Sentient somewhere down
						the line!
					</p>
					<div className="bg-blue-900/30 border border-blue-700/50 text-blue-300 p-4 rounded-md text-sm">
						<div className="flex items-center gap-2">
							<IconInfoCircle size={20} />
							<span>
								Our current focus is on perfecting proactive
								automation with deep personalization.
							</span>
						</div>
					</div>
				</div>
				<p className="text-gray-600 text-xs mt-8 absolute bottom-8">
					Thank you for being a part of the Sentient beta program.
				</p>
			</div>
		</div>
	)
}

export default VoicePage
