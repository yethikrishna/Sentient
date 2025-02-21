/**
 * @file Neo4j database interaction module for fetching graph data.
 * This module sets up a connection to a Neo4j database and provides a function to fetch graph data,
 * transforming it into a format suitable for graph visualization libraries.
 */

import neo4j from "neo4j-driver"

/**
 * Neo4j driver instance configured to connect to the local Neo4j database.
 * It uses Bolt protocol and basic authentication with username 'neo4j' and password 'Gr5sdwdwBWh1WXC'.
 * @constant {neo4j.Driver}
 */
const driver = neo4j.driver(
	"bolt://localhost:7687", // Bolt URL for local Neo4j instance
	neo4j.auth.basic("neo4j", "Gr5sdwdwBWh1WXC") // Basic authentication with username and password
)

/**
 * Fetches graph data from the Neo4j database and formats it for graph visualization.
 *
 * This function establishes a session with the Neo4j database, runs a Cypher query to fetch nodes and relationships,
 * and then transforms the Neo4j response into a structure of nodes and edges that can be used by graph visualization libraries
 * like Vis.js or Cytoscape.js.
 *
 * @async
 * @function fetchGraphData
 * @returns {Promise<{nodes: Array<object>, edges: Array<object>}>} A promise that resolves to an object containing two arrays:
 *   - `nodes`: An array of node objects, each with `id`, `label`, and `properties`.
 *   - `edges`: An array of edge objects, each with `from`, `to`, and `label`.
 * @throws {Error} If there is an error during the database query or data processing, the promise will be rejected.
 *
 * @example
 * // Example usage:
 * fetchGraphData()
 *   .then(graphData => {
 *     console.log('Graph Data:', graphData);
 *     // Use graphData to render a graph visualization
 *   })
 *   .catch(error => {
 *     console.error('Failed to fetch graph data:', error);
 *   });
 */
export const fetchGraphData = async () => {
	/**
	 * Neo4j session instance for executing queries.
	 * @type {neo4j.Session}
	 */
	const session = driver.session()
	try {
		/**
		 * Executes a Cypher query to fetch all nodes and relationships in the graph.
		 * The query `MATCH (n)-[r]->(m) RETURN n, r, m` retrieves all nodes `n` and `m` connected by relationships `r`.
		 * @type {neo4j.Result}
		 */
		const result = await session.run(`MATCH (n)-[r]->(m) RETURN n, r, m`)

		/**
		 * Array to store formatted node data for graph visualization.
		 * @type {Array<object>}
		 */
		const nodes = []
		/**
		 * Array to store formatted edge data for graph visualization.
		 * @type {Array<object>}
		 */
		const edges = []

		// Process each record returned by the Neo4j query
		result.records.forEach((record) => {
			/**
			 * Source node of the relationship, retrieved from the record.
			 * @type {neo4j.Node}
			 */
			const sourceNode = record.get("n")
			/**
			 * Target node of the relationship, retrieved from the record.
			 * @type {neo4j.Node}
			 */
			const targetNode = record.get("m")
			/**
			 * Relationship between the source and target nodes, retrieved from the record.
			 * @type {neo4j.Relationship}
			 */
			const relationship = record.get("r")

			// Format and add source node to the nodes array
			nodes.push({
				id: sourceNode.identity.toString(), // Node ID, converted to string
				label: sourceNode.labels[0], // Node label (assuming single label per node)
				properties: sourceNode.properties // Node properties
			})

			// Format and add target node to the nodes array
			nodes.push({
				id: targetNode.identity.toString(), // Node ID, converted to string
				label: targetNode.labels[0], // Node label (assuming single label per node)
				properties: targetNode.properties // Node properties
			})

			// Format and add edge to the edges array
			edges.push({
				from: sourceNode.identity.toString(), // Source node ID for the edge
				to: targetNode.identity.toString(), // Target node ID for the edge
				label: relationship.type // Relationship type as edge label
			})
		})

		// Return the formatted nodes and edges
		return { nodes, edges }
	} finally {
		// Ensure the session is closed after query execution, regardless of success or failure
		await session.close()
	}
}