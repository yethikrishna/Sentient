"use client"
import React, { useState, useEffect, useCallback } from "react"
import Sidebar from "@components/Sidebar"
import { IconMicrophone, IconInfoCircle, IconMenu2 } from "@tabler/icons-react"
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
		<div className="flex h-screen bg-matteblack dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 bg-matteblack border-b border-neutral-800 md:hidden">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-white"
					>
						<IconMenu2 />
					</button>
					<h1 className="text-lg font-semibold text-white">Voice</h1>
				</header>
				<main className="flex-1 flex flex-col items-center justify-center overflow-y-auto p-4 sm:p-6 text-white relative">
					<div className="text-center p-6 sm:p-8 bg-neutral-900/50 rounded-lg border border-neutral-700 shadow-xl max-w-2xl w-full">
						<IconMicrophone className="w-16 h-16 sm:w-20 sm:h-20 text-lightblue mx-auto mb-6" />
						<h1 className="font-Poppins text-white text-3xl sm:text-4xl font-light mb-4">
							Voice Features Coming Soon!
						</h1>
						<p className="text-gray-300 mb-2 text-base sm:text-lg">
							You're currently using a beta version of Sentient.
						</p>
						<p className="text-gray-400 text-sm sm:text-md mb-6">
							We're hard at work developing a seamless and
							intuitive voice experience. Exciting voice
							interaction capabilities will be added to Sentient
							somewhere down the line!
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
					<p className="text-gray-600 text-xs mt-8 absolute bottom-8 px-4 text-center">
						Thank you for being a part of the Sentient beta program.
					</p>
				</main>
			</div>
		</div>
	)
}

export default VoicePage
