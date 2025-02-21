import { useEffect, useRef } from "react" // Importing React hooks: useEffect, useRef
import { DataSet, Network } from "vis-network/standalone" // Importing DataSet and Network classes from vis-network library
import React from "react"

/**
 * GraphVisualization Component - Renders a knowledge graph using vis-network library.
 *
 * This component takes nodes and edges data as props and visualizes them as an interactive graph.
 * It uses the vis-network library to create and manage the graph, providing options for styling,
 * interaction, and physics simulation. The graph is rendered within a div element, and the component
 * handles the lifecycle for graph initialization and updates based on changes in nodes and edges data.
 *
 * @param {object} props - Component props.
 * @param {Array<object>} props.nodes - Array of node objects for the graph. Each node should have an 'id' and optional 'label' or 'properties.name'.
 * @param {Array<object>} props.edges - Array of edge objects for the graph. Each edge should have 'from', 'to', and optional 'label' or 'properties.type'.
 * @returns {React.ReactNode} - The GraphVisualization component UI.
 */
const GraphVisualization = ({ nodes, edges }) => {
	const networkRef = useRef() // useRef to hold the network instance for vis-network - networkRef: React.RefObject<Network>

	/**
	 * useEffect hook to initialize and update the vis-network graph.
	 *
	 * This hook runs after the component renders. It initializes the vis-network instance,
	 * sets up the data (nodes and edges) for the graph, configures options for styling and interaction,
	 * and renders the graph in the specified container div. The graph is updated whenever the `nodes` or `edges` props change.
	 */
	useEffect(() => {
		const container = networkRef.current // Get the current DOM element reference for the graph container

		// Remove duplicate nodes based on 'id' to ensure unique nodes in the graph data
		const uniqueNodes = [
			...new Map(
				nodes.map((node) => [node.id, node]) // Create a Map to filter nodes by 'id'
			).values() // Extract unique node values from the Map
		]

		// Remove duplicate edges based on 'from' and 'to' node combination to ensure unique edges
		const uniqueEdges = [
			...new Map(
				edges.map((edge) => [
					`${edge.from}-${edge.to}`, // Create a unique key for each edge based on 'from' and 'to'
					edge // Edge object as value
				])
			).values() // Extract unique edge values from the Map
		]

		// Data object for vis-network, containing DataSet instances for nodes and edges
		const data = {
			nodes: new DataSet(
				uniqueNodes.map((node) => ({
					id: node.id, // Node ID from input data
					label: node.properties?.name || node.label || "Node", // Node label, prioritize 'properties.name', then 'label', default to "Node"
					shape: "dot", // Node shape set to 'dot'
					size: 20 // Node size set to 20
				}))
			),
			edges: new DataSet(
				uniqueEdges.map((edge) => ({
					from: edge.from, // Edge source node ID
					to: edge.to, // Edge target node ID
					label: edge.label || edge.properties?.type || "", // Edge label, prioritize 'label', then 'properties.type', default to empty string
					arrows: "to" // Edge arrows, directed towards 'to' node
				}))
			)
		}

		// Options object for vis-network, configuring visual and interactive properties of the graph
		const options = {
			nodes: {
				font: {
					size: 16, // Node label font size
					color: "#ffffff" // Node label font color white
				},
				color: {
					border: "#0057FF", // Node border color blue
					background: "#00B2FE" // Node background color light blue
				},
				shape: "circle" // Default node shape is circle
			},
			edges: {
				font: {
					align: "middle", // Edge label alignment to middle of edge
					size: 14, // Edge label font size
					color: "#333333" // Edge label font color dark gray
				},
				color: "#00B2FE", // Edge color light blue
				arrows: {
					to: {
						enabled: true, // Directed edges, arrows pointing to target node
						scaleFactor: 1 // Arrow size scale factor
					}
				}
			},
			interaction: {
				hover: true, // Enable hover interactions
				navigationButtons: true, // Enable navigation buttons on the canvas
				keyboard: true // Enable keyboard navigation
			},
			physics: {
				enabled: true, // Enable physics simulation for graph layout
				solver: "forceAtlas2Based", // Physics solver algorithm
				stabilization: {
					iterations: 150 // Stabilization iterations for graph layout
				}
			}
		}

		// Initialize vis-network Network instance with container, data, and options
		new Network(container, data, options)
	}, [nodes, edges]) // useEffect dependency array: effect runs when 'nodes' or 'edges' change

	return <div ref={networkRef} className="w-full h-full" /> // Div element to hold the vis-network graph, ref attached, full width and height
}

export default GraphVisualization
