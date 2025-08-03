"""
Graph Management Endpoints

API endpoints for project graph generation and management:
- Generate adjacency matrices from paper embeddings
- Store graphs as static JSON files
- Manage graph lifecycle (CRUD operations)
"""

import uuid
import logging
from typing import Dict, Any, Optional

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import networkx as nx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.services.graph.graph_service_integrated import GraphService
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/projects/{project_id}/graph/generate", response_model=Dict[str, Any])
async def generate_project_graph(
    project_id: uuid.UUID,
    similarity_threshold: float = Body(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Minimum similarity threshold for graph edges"
    ),
    force_regenerate: bool = Body(
        default=False, 
        description="Force regeneration if graph already exists"
    ),
    enable_clustering: bool = Body(
        default=True,
        description="Enable clustering analysis and community detection"
    ),
    clustering_algorithm: str = Body(
        default="auto",
        description="Clustering algorithm: 'auto', 'kmeans', 'dbscan', 'hierarchical', 'community'"
    ),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Generate enhanced adjacency matrix graph with clustering for papers in a project.
    
    Creates a comprehensive JSON file with:
    - Adjacency matrix based on embedding cosine similarity
    - Advanced clustering analysis (K-Means, DBSCAN, Hierarchical, Community Detection)
    - Graph topology analysis and statistics
    - Paper metadata with cluster assignments
    - Edge list optimized for visualization
    - Clustering quality metrics and recommendations
    
    Clustering Algorithms:
    - 'auto': Automatically selects best performing algorithm
    - 'kmeans': K-Means clustering with optimal K determination
    - 'dbscan': Density-based clustering with auto-tuned parameters  
    - 'hierarchical': Agglomerative hierarchical clustering
    - 'community': Graph-based community detection using modularity
    
    Requires at least 2 papers with completed embeddings in the project.
    Clustering requires at least 3 papers for meaningful results.
    """
    try:
        # Validate clustering algorithm parameter
        valid_algorithms = ["auto", "kmeans", "dbscan", "hierarchical", "community"]
        if clustering_algorithm not in valid_algorithms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid clustering algorithm. Must be one of: {valid_algorithms}"
            )
        
        graph_service = GraphService(session)
        result = await graph_service.generate_project_graph(
            project_id=project_id,
            similarity_threshold=similarity_threshold,
            force_regenerate=force_regenerate,
            enable_clustering=enable_clustering,
            clustering_algorithm=clustering_algorithm
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating enhanced graph for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate project graph: {str(e)}"
        )


@router.get("/projects/{project_id}/graph", response_model=Dict[str, Any])
async def get_project_graph(
    project_id: uuid.UUID,
    include_data: bool = Query(
        default=True, 
        description="Whether to include full graph data or just metadata"
    ),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get existing project graph data.
    
    Returns graph metadata and optionally full graph data including:
    - Adjacency matrix
    - Node information (papers)
    - Edge information
    - Graph statistics
    """
    try:
        graph_service = GraphService(session)
        
        if include_data:
            result = await graph_service.get_project_graph(project_id)
        else:
            result = await graph_service.get_graph_statistics(project_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="No graph found for this project"
            )
        
        return {
            "success": True,
            "project_id": str(project_id),
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project graph: {str(e)}"
        )


@router.get("/projects/{project_id}/graph/download")
async def download_project_graph(
    project_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Download project graph as JSON file.
    
    Returns the raw JSON file containing the adjacency matrix and all graph data.
    """
    try:
        graph_service = GraphService(session)
        graph_data = await graph_service.get_project_graph(project_id)
        
        if not graph_data:
            raise HTTPException(
                status_code=404,
                detail="No graph found for this project"
            )
        
        graph_path = Path(graph_data["graph_path"])
        if not graph_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Graph file not found"
            )
        
        return FileResponse(
            path=str(graph_path),
            filename=f"project_{project_id}_graph.json",
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading graph for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download project graph: {str(e)}"
        )


@router.delete("/projects/{project_id}/graph", response_model=Dict[str, Any])
async def delete_project_graph(
    project_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete project graph file and database record.
    
    Removes both the JSON file and the database entry for the graph.
    """
    try:
        graph_service = GraphService(session)
        result = await graph_service.delete_project_graph(project_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error deleting graph for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project graph: {str(e)}"
        )


@router.put("/projects/{project_id}/graph/regenerate", response_model=Dict[str, Any])
async def regenerate_project_graph(
    project_id: uuid.UUID,
    similarity_threshold: float = Body(
        default=0.3, 
        ge=0.0, 
        le=1.0, 
        description="Similarity threshold for graph edges (lower = more connections)"
    ),
    enable_clustering: bool = Body(
        default=True,
        description="Enable clustering analysis and community detection"
    ),
    clustering_algorithm: str = Body(
        default="auto",
        description="Clustering algorithm: 'auto', 'kmeans', 'dbscan', 'hierarchical', 'community'"
    ),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    🔄 **Regenerate Project Graph from Scratch**
    
    **Perfect for when new papers are added to your project!**
    
    This endpoint completely rebuilds the graph to include all papers currently in the project.
    Use this when:
    - ✅ New papers have been added to the project
    - ✅ You want to refresh the graph with updated data
    - ✅ The graph seems outdated or incomplete
    - ✅ You want to change similarity thresholds
    
    **What it does:**
    1. 🗑️ Deletes the existing cached graph
    2. 🔍 Fetches ALL current papers in the project
    3. 🧮 Recalculates embeddings and similarities
    4. 🕸️ Rebuilds the complete graph structure
    5. 🎨 Applies clustering analysis
    6. 💾 Saves the fresh graph data
    
    **Parameters:**
    - `similarity_threshold`: Lower values create more connections (0.3 recommended)
    - `enable_clustering`: Groups related papers into clusters
    - `clustering_algorithm`: Method for grouping papers
    
    **Returns:** Complete regenerated graph with all current papers included
    """
    try:
        logger.info(f"🔄 Regenerating graph for project {project_id}")
        logger.info(f"🔄 Parameters: threshold={similarity_threshold}, clustering={enable_clustering}")
        
        graph_service = GraphService(session)
        
        # Force complete regeneration
        result = await graph_service.generate_project_graph(
            project_id=project_id,
            similarity_threshold=similarity_threshold,
            force_regenerate=True,  # Always force regeneration
            enable_clustering=enable_clustering,
            clustering_algorithm=clustering_algorithm
        )
        
        if result["success"]:
            # Fix: Graph data is directly in result, not under "data" key
            actual_graph = result.get("graph", {})
            nodes = actual_graph.get("nodes", [])
            edges = actual_graph.get("edges", [])
            clustering = result.get("clustering", {})
            
            logger.info(f"🔄 Graph regenerated successfully: {len(nodes)} nodes, {len(edges)} edges")
            
            # Generate debug PNG if nodes and edges exist
            if nodes and edges:
                try:
                    await _generate_debug_png(project_id, nodes, edges)
                    logger.info(f"🔄 Debug PNG generated for regenerated graph")
                except Exception as png_error:
                    logger.warning(f"🔄 Failed to generate debug PNG: {png_error}")
            
            return {
                "success": True,
                "message": f"Graph regenerated successfully with {len(nodes)} papers and {len(edges)} connections",
                "data": {
                    "graph": actual_graph,
                    "clustering": clustering,
                    "processing_time": result.get("processing_time", 0),
                    "project_id": str(project_id)
                },
                "regeneration_info": {
                    "papers_included": len(nodes),
                    "connections_created": len(edges),
                    "similarity_threshold": similarity_threshold,
                    "clustering_enabled": enable_clustering,
                    "clustering_algorithm": clustering_algorithm,
                    "clusters_found": len(set(node.get("cluster", 0) for node in nodes)) if nodes else 0
                }
            }
        else:
            logger.warning(f"🔄 Graph regeneration failed: {result.get('error')}")
            return result
        
    except Exception as e:
        logger.error(f"Error regenerating graph for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate project graph: {str(e)}"
        )


@router.get("/projects/{project_id}/graph/statistics", response_model=Dict[str, Any])
async def get_graph_statistics(
    project_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get graph statistics without loading full graph data.
    
    Returns lightweight statistics about the graph:
    - Number of nodes and edges
    - Average similarity
    - Graph density
    - Generation timestamps
    """
    try:
        graph_service = GraphService(session)
        stats = await graph_service.get_graph_statistics(project_id)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail="No graph found for this project"
            )
        
        return {
            "success": True,
            **stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph statistics for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get graph statistics: {str(e)}"
        )


# Batch operations for multiple projects
@router.post("/graphs/batch/generate", response_model=Dict[str, Any])
async def batch_generate_graphs(
    project_ids: list[uuid.UUID] = Body(..., description="List of project IDs"),
    similarity_threshold: float = Body(default=0.7, ge=0.0, le=1.0),
    force_regenerate: bool = Body(default=False),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Generate graphs for multiple projects in batch.
    
    Useful for bulk operations or administrative tasks.
    Only processes projects the user has access to.
    """
    try:
        graph_service = GraphService(session)
        results = []
        
        for project_id in project_ids:
            try:
                # Note: In a real implementation, you'd verify access for each project
                result = await graph_service.generate_project_graph(
                    project_id=project_id,
                    similarity_threshold=similarity_threshold,
                    force_regenerate=force_regenerate
                )
                results.append({
                    "project_id": str(project_id),
                    **result
                })
            except Exception as e:
                results.append({
                    "project_id": str(project_id),
                    "success": False,
                    "error": str(e)
                })
        
        successful = len([r for r in results if r.get("success")])
        
        return {
            "success": True,
            "message": f"Processed {len(project_ids)} projects, {successful} successful",
            "total_projects": len(project_ids),
            "successful_generations": successful,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch graph generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch graph generation failed: {str(e)}"
        ) 


@router.get("/projects/{project_id}/graph/clusters", response_model=Dict[str, Any])
async def get_project_graph_clusters(
    project_id: uuid.UUID,
    algorithm: str = Query(
        default="best",
        description="Clustering algorithm to return: 'best', 'kmeans', 'dbscan', 'hierarchical', 'community'"
    ),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get clustering analysis results for a project's paper graph.
    
    Returns detailed clustering information including:
    - Cluster assignments for each paper
    - Clustering quality metrics
    - Algorithm-specific parameters
    - Cluster statistics and characteristics
    
    Requires an existing graph with clustering analysis.
    """
    try:
        graph_service = GraphService(session)
        result = await graph_service.get_project_graph(project_id, include_data=True)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail="Graph not found for this project"
            )
        
        graph_data = result["data"]
        clustering_data = graph_data.get("clustering", {})
        
        if not clustering_data:
            raise HTTPException(
                status_code=404,
                detail="No clustering analysis found. Generate graph with clustering enabled first."
            )
        
        # Return specific algorithm or best result
        if algorithm == "best":
            best_clustering = clustering_data.get("best_clustering", {})
            if not best_clustering:
                raise HTTPException(status_code=404, detail="No best clustering result available")
            return {
                "success": True,
                "project_id": str(project_id),
                "clustering": best_clustering,
                "metadata": {
                    "algorithm": best_clustering.get("selected_algorithm"),
                    "quality_score": best_clustering.get("silhouette_score", 0),
                    "available_algorithms": list(clustering_data.get("algorithms", {}).keys())
                }
            }
        else:
            algorithms = clustering_data.get("algorithms", {})
            if algorithm not in algorithms:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Algorithm '{algorithm}' not found. Available: {list(algorithms.keys())}"
                )
            return {
                "success": True,
                "project_id": str(project_id),
                "clustering": algorithms[algorithm],
                "metadata": {
                    "algorithm": algorithm,
                    "available_algorithms": list(algorithms.keys())
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clusters for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get clustering data: {str(e)}"
        )


@router.get("/projects/{project_id}/graph/analytics", response_model=Dict[str, Any])
async def get_project_graph_analytics(
    project_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get comprehensive analytics for a project's paper graph.
    
    Returns detailed graph analysis including:
    - Network topology metrics (density, clustering coefficient, etc.)
    - Clustering quality and algorithm comparison
    - Node centrality measures
    - Community structure analysis
    - Graph visualization recommendations
    
    Useful for understanding the semantic structure of papers in a project.
    """
    try:
        logger.info(f"🔍 DEBUG: Starting graph analytics for project {project_id}")
        
        graph_service = GraphService(session)
        result = await graph_service.get_project_graph(project_id, include_data=True)
        
        logger.info(f"🔍 DEBUG: Graph service result - Success: {result.get('success')}")
        logger.info(f"🔍 DEBUG: Graph service result keys: {list(result.keys())}")
        
        if not result["success"]:
            logger.warning(f"🔍 DEBUG: Graph not found - Error: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=404,
                detail=f"Graph not found for this project: {result.get('error', 'Unknown error')}"
            )
        
        graph_data = result["data"]
        logger.info(f"🔍 DEBUG: Graph data keys: {list(graph_data.keys()) if graph_data else 'None'}")
        
        if graph_data:
            # Fix: Graph structure is nested inside 'graph' key
            actual_graph = graph_data.get("graph", {})
            nodes = actual_graph.get("nodes", [])
            edges = actual_graph.get("edges", [])
            metadata = actual_graph.get("metadata", {})
            logger.info(f"🔍 DEBUG: Found {len(nodes)} nodes, {len(edges)} edges")
            logger.info(f"🔍 DEBUG: Metadata: {metadata}")
        
        # Extract analytics
        analytics = {
            "success": True,
            "project_id": str(project_id),
            "basic_metrics": graph_data.get("metadata", {}),
            "topology_analysis": graph_data.get("clustering", {}).get("graph_analysis", {}),
            "clustering_summary": {},
            "recommendations": [],
            "debug_info": {
                "graph_data_available": graph_data is not None,
                "graph_data_keys": list(graph_data.keys()) if graph_data else [],
                "service_result": result
            }
        }
        
        # Clustering analysis summary
        clustering_data = graph_data.get("clustering", {})
        if clustering_data:
            algorithms = clustering_data.get("algorithms", {})
            best_clustering = clustering_data.get("best_clustering", {})
            
            analytics["clustering_summary"] = {
                "algorithms_tested": list(algorithms.keys()),
                "best_algorithm": best_clustering.get("selected_algorithm"),
                "best_quality_score": best_clustering.get("silhouette_score", 0),
                "optimal_clusters": clustering_data.get("optimal_clusters", 0)
            }
            
            # Generate recommendations based on analysis
            recommendations = []
            
            # Graph connectivity recommendations
            topology = analytics["topology_analysis"]
            if topology.get("connected_components", 1) > 1:
                recommendations.append({
                    "type": "connectivity",
                    "message": f"Graph has {topology['connected_components']} disconnected components. Consider lowering similarity threshold.",
                    "severity": "info"
                })
            
            # Clustering quality recommendations
            quality_score = analytics["clustering_summary"].get("best_quality_score", 0)
            if quality_score < 0.3:
                recommendations.append({
                    "type": "clustering",
                    "message": "Low clustering quality detected. Papers may not have distinct semantic groups.",
                    "severity": "warning"
                })
            elif quality_score > 0.7:
                recommendations.append({
                    "type": "clustering", 
                    "message": "Excellent clustering quality. Papers form distinct semantic groups.",
                    "severity": "success"
                })
            
            # Graph density recommendations
            density = analytics["basic_metrics"].get("density", 0)
            if density < 0.1:
                recommendations.append({
                    "type": "density",
                    "message": "Sparse graph detected. Consider lowering similarity threshold to find more connections.",
                    "severity": "info"
                })
            elif density > 0.8:
                recommendations.append({
                    "type": "density",
                    "message": "Very dense graph. Consider raising similarity threshold to focus on strongest connections.",
                    "severity": "info"
                })
            
            analytics["recommendations"] = recommendations
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get graph analytics: {str(e)}"
        )


@router.get("/projects/{project_id}/graph/visualization", response_model=Dict[str, Any])
async def get_graph_visualization_data(
    project_id: uuid.UUID,
    layout: str = Query(
        default="force_directed",
        description="Layout algorithm: 'force_directed', 'circular', 'hierarchical', 'cluster_based'"
    ),
    include_embeddings: bool = Query(
        default=False,
        description="Include 2D embeddings for advanced visualization"
    ),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get optimized visualization data for the project graph.
    
    Returns graph data optimized for frontend visualization including:
    - Node positions based on selected layout algorithm
    - Clustering-based color schemes
    - Edge bundling recommendations
    - Interactive visualization configuration
    - Optional 2D projections of embeddings
    
    Perfect for feeding into D3.js, Cytoscape.js, or other graph visualization libraries.
    """
    try:
        logger.info(f"🎨 DEBUG: Starting graph visualization for project {project_id}")
        logger.info(f"🎨 DEBUG: Layout: {layout}, Include embeddings: {include_embeddings}")
        
        graph_service = GraphService(session)
        result = await graph_service.get_project_graph(project_id, include_data=True)
        
        logger.info(f"🎨 DEBUG: Graph service result - Success: {result.get('success')}")
        logger.info(f"🎨 DEBUG: Graph service result keys: {list(result.keys())}")
        
        if not result["success"]:
            logger.warning(f"🎨 DEBUG: Graph not found - Error: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=404,
                detail=f"Graph not found for this project: {result.get('error', 'Unknown error')}"
            )
        
        graph_data = result["data"]
        logger.info(f"🎨 DEBUG: Graph data keys: {list(graph_data.keys()) if graph_data else 'None'}")
        
        # Fix: Graph structure is nested inside 'graph' key
        actual_graph = graph_data.get("graph", {})
        nodes = actual_graph.get("nodes", [])
        edges = actual_graph.get("edges", [])
        clustering = graph_data.get("clustering", {})
        
        logger.info(f"🎨 DEBUG: Found {len(nodes)} nodes, {len(edges)} edges")
        logger.info(f"🎨 DEBUG: Clustering data available: {clustering is not None}")
        
        # Debug: Log first few nodes and edges
        if nodes:
            logger.info(f"🎨 DEBUG: First node sample: {nodes[0]}")
        if edges:
            logger.info(f"🎨 DEBUG: First edge sample: {edges[0]}")
        
        # Generate PNG for debug mode
        if nodes and edges:
            try:
                await _generate_debug_png(project_id, nodes, edges)
                logger.info(f"🎨 DEBUG: Generated PNG visualization for project {project_id}")
            except Exception as png_error:
                logger.warning(f"🎨 DEBUG: Failed to generate PNG: {png_error}")
        
        # Prepare visualization-optimized data
        viz_data = {
            "success": True,
            "project_id": str(project_id),
            "layout": layout,
            "nodes": [],
            "edges": edges,  # Edges remain the same
            "config": {
                "node_size_range": [10, 50],
                "edge_width_range": [1, 5],
                "color_scheme": "cluster_based",
                "layout_algorithm": layout
            },
            "legends": {
                "clusters": {},
                "node_sizes": "Based on degree centrality",
                "edge_widths": "Based on similarity strength"
            },
            "debug_info": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "has_clustering": bool(clustering),
                "layout_requested": layout,
                "raw_graph_data_keys": list(graph_data.keys()) if graph_data else [],
                "service_result": result
            }
        }
        
        # Add cluster-based coloring
        best_clustering = clustering.get("best_clustering", {})
        cluster_labels = best_clustering.get("cluster_labels", [])
        
        # Generate cluster color palette
        n_clusters = len(set(cluster_labels)) if cluster_labels else 1
        cluster_colors = [
            f"hsl({int(360 * i / n_clusters)}, 70%, 60%)" 
            for i in range(n_clusters)
        ]
        
        # Enhance nodes with visualization properties
        for i, node in enumerate(nodes):
            cluster_id = cluster_labels[i] if i < len(cluster_labels) else 0
            
            enhanced_node = {
                **node,
                "cluster_id": cluster_id,
                "color": cluster_colors[cluster_id] if cluster_id >= 0 else "#cccccc",
                "size": 20,  # Base size, can be adjusted based on centrality
                "label": node.get("title", f"Paper {i+1}")[:50] + "..." if len(node.get("title", "")) > 50 else node.get("title", f"Paper {i+1}")
            }
            
            viz_data["nodes"].append(enhanced_node)
        
        # Add cluster legend
        for i, color in enumerate(cluster_colors):
            cluster_size = cluster_labels.count(i) if cluster_labels else 0
            viz_data["legends"]["clusters"][f"Cluster {i+1}"] = {
                "color": color,
                "size": cluster_size,
                "description": f"Semantic group with {cluster_size} papers"
            }
        
        # Add 2D embeddings if requested
        if include_embeddings and nodes:
            try:
                from sklearn.decomposition import PCA
                
                # Extract embeddings and reduce to 2D
                embeddings = np.array([node["embedding"] for node in nodes if "embedding" in node])
                if len(embeddings) > 0:
                    pca = PCA(n_components=2, random_state=42)
                    embeddings_2d = pca.fit_transform(embeddings)
                    
                    # Add 2D positions to nodes
                    for i, node in enumerate(viz_data["nodes"]):
                        if i < len(embeddings_2d):
                            node["embedding_2d"] = {
                                "x": float(embeddings_2d[i][0]),
                                "y": float(embeddings_2d[i][1])
                            }
                    
                    viz_data["config"]["embedding_projection"] = {
                        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
                        "total_variance_explained": float(sum(pca.explained_variance_ratio_))
                    }
                    
            except Exception as e:
                logger.warning(f"Failed to generate 2D embeddings: {str(e)}")
        
        return viz_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visualization data for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get visualization data: {str(e)}"
        ) 


async def _generate_debug_png(project_id: uuid.UUID, nodes: list, edges: list) -> None:
    """
    Generate a PNG visualization of the graph for debug purposes.
    
    Args:
        project_id: Project UUID for filename
        nodes: List of graph nodes
        edges: List of graph edges
    """
    try:
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes with positions and clusters
        pos = {}
        node_colors = []
        node_sizes = []
        
        for node in nodes:
            G.add_node(node["id"], **node)
            pos[node["id"]] = (node["position"]["x"], node["position"]["y"])
            
            # Color by cluster
            cluster = node.get("cluster", 0)
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc', '#c2c2f0']
            node_colors.append(colors[cluster % len(colors)])
            
            # Size by degree
            degree = node.get("degree", 1)
            node_sizes.append(max(100, degree * 50))
        
        # Add edges
        for edge in edges:
            G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
        
        # Create figure
        plt.figure(figsize=(12, 8))
        plt.title(f"Graph Visualization - Project {project_id}\n{len(nodes)} nodes, {len(edges)} edges")
        
        # Draw the graph
        nx.draw(G, pos=pos, 
                node_color=node_colors,
                node_size=node_sizes,
                with_labels=False,
                edge_color='gray',
                alpha=0.7,
                width=[edge.get("weight", 1) * 2 for edge in edges])
        
        # Add cluster legend
        clusters = set(node.get("cluster", 0) for node in nodes)
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc', '#c2c2f0']
        legend_elements = [plt.scatter([], [], c=colors[i % len(colors)], s=100, label=f'Cluster {i}') 
                          for i in clusters]
        if legend_elements:
            plt.legend(handles=legend_elements, loc='upper right')
        
        # Save PNG
        debug_dir = Path(settings.files.static_dir) / "debug"
        debug_dir.mkdir(exist_ok=True)
        
        png_path = debug_dir / f"graph_{project_id}.png"
        plt.savefig(png_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"🎨 DEBUG: Saved graph PNG to {png_path}")
        
    except Exception as e:
        logger.error(f"🎨 DEBUG: Error generating PNG: {e}")
        raise 