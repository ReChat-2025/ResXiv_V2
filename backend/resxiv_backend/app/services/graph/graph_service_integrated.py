"""
Graph Service Integrated - L6 Engineering Standards
Orchestrates specialized graph sub-services with clean separation of concerns.
"""

import uuid
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors
from app.config.settings import get_settings

from .graph_generation_service import GraphGenerationService
from .graph_clustering_service import GraphClusteringService

logger = logging.getLogger(__name__)
settings = get_settings()


class GraphService:
    """
    Integrated graph service orchestrating specialized sub-services.
    
    Follows Composition over Inheritance principle with clean separation:
    - Generation service: Core graph creation and adjacency matrices
    - Clustering service: ML-based clustering algorithms and analysis
    
    Single point of access for all graph operations while maintaining
    focused, testable components.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.graphs_dir = settings.files.static_dir / "graphs"
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize specialized services
        self.generation_service = GraphGenerationService(session)
        self.clustering_service = GraphClusteringService(session)
    
    # ================================
    # MAIN GRAPH OPERATIONS
    # ================================
    
    async def generate_project_graph(
        self,
        project_id: uuid.UUID,
        similarity_threshold: float = 0.3,
        force_regenerate: bool = False,
        enable_clustering: bool = True,
        clustering_algorithm: str = "auto"
    ) -> Dict[str, Any]:
        """
        Generate enhanced graph with clustering for papers in a project.
        
        Args:
            project_id: Project ID to generate graph for
            similarity_threshold: Minimum similarity for edge connection
            force_regenerate: Whether to force regeneration if graph exists
            enable_clustering: Whether to perform clustering analysis
            clustering_algorithm: Algorithm choice ('auto', 'kmeans', 'dbscan', 'hierarchical')
            
        Returns:
            Graph generation result with clustering and enhanced analytics
        """
        try:
            logger.info(f"Generating enhanced paper graph for project: {project_id}")
            
            # Check if graph already exists
            if not force_regenerate:
                existing_graph = await self._get_existing_graph(project_id)
                if existing_graph:
                    return {
                        "success": True,
                        "cached": True,
                        "graph": existing_graph,
                        "message": "Retrieved cached graph"
                    }
            
            # Generate base graph using generation service
            graph_result = await self.generation_service.generate_project_graph(
                project_id=project_id,
                similarity_threshold=similarity_threshold,
                force_regenerate=force_regenerate
            )
            
            if not graph_result["success"]:
                return graph_result
            
            # Add clustering analysis if enabled
            if enable_clustering and len(graph_result["graph"]["nodes"]) >= 3:
                papers_data = await self.generation_service._get_project_papers_with_embeddings(project_id)
                
                clustering_result = await self.clustering_service.perform_clustering_analysis(
                    papers_data=papers_data,
                    clustering_algorithm=clustering_algorithm
                )
                
                if clustering_result["success"]:
                    # Enhance graph with clustering information
                    enhanced_graph = await self._enhance_graph_with_clustering(
                        graph_result["graph"],
                        clustering_result
                    )
                    graph_result["graph"] = enhanced_graph
                    graph_result["clustering"] = clustering_result
                else:
                    graph_result["clustering"] = {
                        "success": False,
                        "error": clustering_result.get("error", "Clustering failed")
                    }
            
            # Save enhanced graph
            save_result = await self._save_graph_record(project_id, graph_result)
            if save_result["success"]:
                graph_result["graph_file"] = save_result["file_path"]
                graph_result["graph_id"] = save_result["graph_id"]
            
            return graph_result
            
        except Exception as e:
            logger.error(f"Error generating enhanced project graph: {e}")
            return {
                "success": False,
                "error": f"Failed to generate enhanced graph: {str(e)}"
            }
    
    async def get_project_graph(self, project_id: uuid.UUID, include_data: bool = True) -> Dict[str, Any]:
        """
        Get project graph with auto-generation fallback.
        
        Args:
            project_id: Project UUID
            include_data: Whether to include full graph data or just metadata
            
        Returns:
            Graph response with success status and data/metadata
        """
        try:
            logger.info(f"📊 DEBUG: Getting project graph for {project_id}, include_data={include_data}")
            
            graph_data = await self._get_existing_graph(project_id)
            
            logger.info(f"📊 DEBUG: Existing graph found: {graph_data is not None}")
            
            if not graph_data:
                logger.info(f"📊 DEBUG: Graph not found for project {project_id}, attempting auto-generation")
                
                # Try to auto-generate the graph
                generation_result = await self.generate_project_graph(
                    project_id=project_id,
                    similarity_threshold=0.3,
                    force_regenerate=False,
                    enable_clustering=True,
                    clustering_algorithm="auto"
                )
                
                logger.info(f"📊 DEBUG: Auto-generation result - Success: {generation_result.get('success')}")
                logger.info(f"📊 DEBUG: Auto-generation result keys: {list(generation_result.keys())}")
                
                if generation_result["success"]:
                    graph_data = generation_result["graph"]
                    logger.info(f"📊 DEBUG: Successfully auto-generated graph for project {project_id}")
                    if graph_data:
                        logger.info(f"📊 DEBUG: Generated graph has keys: {list(graph_data.keys())}")
                        logger.info(f"📊 DEBUG: Generated graph nodes: {len(graph_data.get('nodes', []))}")
                        logger.info(f"📊 DEBUG: Generated graph edges: {len(graph_data.get('edges', []))}")
                else:
                    logger.error(f"📊 DEBUG: Auto-generation failed: {generation_result.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": f"Graph not found and auto-generation failed: {generation_result.get('error', 'Unknown error')}"
                    }
            else:
                logger.info(f"📊 DEBUG: Using existing graph data with keys: {list(graph_data.keys())}")
            
            if include_data:
                logger.info(f"📊 DEBUG: Returning full graph data")
                return {
                    "success": True,
                    "data": graph_data
                }
            else:
                # Return only metadata for lightweight response
                metadata = graph_data.get("metadata", {})
                logger.info(f"📊 DEBUG: Returning metadata only: {metadata}")
                return {
                    "success": True,
                    "metadata": metadata,
                    "node_count": len(graph_data.get("nodes", [])),
                    "edge_count": len(graph_data.get("edges", []))
                }
                
        except Exception as e:
            logger.error(f"📊 DEBUG: Error getting project graph: {e}")
            return {"success": False, "error": f"Failed to get project graph: {str(e)}"}
    
    async def delete_project_graph(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Delete project graph and associated files.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Deletion result
        """
        try:
            # Find and delete graph file
            graph_file = self.graphs_dir / f"project_{project_id}_graph.json"
            
            if graph_file.exists():
                graph_file.unlink()
                logger.info(f"Deleted graph file for project {project_id}")
            
            return {
                "success": True,
                "message": f"Graph for project {project_id} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting project graph: {e}")
            return {
                "success": False,
                "error": f"Failed to delete graph: {str(e)}"
            }
    
    # ================================
    # GRAPH ANALYTICS AND STATISTICS
    # ================================
    
    async def get_graph_statistics(self, project_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive graph statistics.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Graph statistics
        """
        try:
            graph_data = await self._get_existing_graph(project_id)
            
            if not graph_data:
                return None
            
            # Extract basic metrics
            basic_stats = {
                "node_count": len(graph_data.get("nodes", [])),
                "edge_count": len(graph_data.get("edges", [])),
                "has_clustering": "clustering" in graph_data,
                "generated_at": graph_data.get("generated_at"),
                "similarity_threshold": graph_data.get("parameters", {}).get("similarity_threshold")
            }
            
            # Add clustering statistics if available
            clustering_stats = {}
            if "clustering" in graph_data and graph_data["clustering"]["success"]:
                clustering_info = graph_data["clustering"]
                clustering_stats = {
                    "algorithm_used": clustering_info.get("algorithm_used"),
                    "number_of_clusters": clustering_info.get("cluster_analysis", {}).get("summary", {}).get("total_clusters"),
                    "silhouette_score": clustering_info.get("quality_metrics", {}).get("silhouette_score"),
                    "largest_cluster_size": clustering_info.get("cluster_analysis", {}).get("summary", {}).get("largest_cluster_size")
                }
            
            # Add graph topology metrics
            topology_stats = graph_data.get("metrics", {})
            
            return {
                "basic": basic_stats,
                "clustering": clustering_stats,
                "topology": topology_stats,
                "project_id": str(project_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return None
    
    # ================================
    # HELPER METHODS
    # ================================
    
    async def _enhance_graph_with_clustering(
        self,
        graph_data: Dict[str, Any],
        clustering_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance graph data with clustering information.
        
        Args:
            graph_data: Base graph data
            clustering_result: Clustering analysis result
            
        Returns:
            Enhanced graph data
        """
        try:
            # Add cluster information to nodes
            cluster_labels = clustering_result.get("cluster_labels", [])
            nodes = graph_data.get("nodes", [])
            
            for i, node in enumerate(nodes):
                if i < len(cluster_labels):
                    node["cluster"] = int(cluster_labels[i])
                    node["cluster_color"] = self._get_cluster_color(cluster_labels[i])
            
            # Add clustering metadata
            graph_data["clustering_enabled"] = True
            graph_data["clustering_algorithm"] = clustering_result.get("algorithm_used")
            
            # Add cluster visualization if available
            if "visualization" in clustering_result:
                graph_data["cluster_visualization"] = clustering_result["visualization"]
            
            return graph_data
            
        except Exception as e:
            logger.warning(f"Error enhancing graph with clustering: {e}")
            return graph_data
    
    def _get_cluster_color(self, cluster_label: int) -> str:
        """
        Get color for cluster visualization.
        
        Args:
            cluster_label: Cluster label
            
        Returns:
            Color hex code
        """
        # Color palette for clusters
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
            "#F8C471", "#82E0AA", "#F1948A", "#85C1E9", "#D2B4DE"
        ]
        
        if cluster_label == -1:  # Noise points (DBSCAN)
            return "#CCCCCC"
        
        return colors[cluster_label % len(colors)]
    
    async def _get_existing_graph(self, project_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get existing graph from file system.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Graph data or None
        """
        try:
            graph_file = self.graphs_dir / f"project_{project_id}_graph.json"
            
            if graph_file.exists():
                with open(graph_file, 'r') as f:
                    graph_data = json.load(f)
                return graph_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading existing graph: {e}")
            return None
    
    async def _save_graph_record(
        self,
        project_id: uuid.UUID,
        graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save graph data to file system.
        
        Args:
            project_id: Project UUID
            graph_data: Graph data to save
            
        Returns:
            Save result
        """
        try:
            graph_file = self.graphs_dir / f"project_{project_id}_graph.json"
            
            # Add metadata
            graph_data["saved_at"] = datetime.utcnow().isoformat()
            graph_data["project_id"] = str(project_id)
            
            # Save to file
            with open(graph_file, 'w') as f:
                json.dump(graph_data, f, indent=2, default=str)
            
            return {
                "success": True,
                "file_path": str(graph_file),
                "graph_id": str(project_id)
            }
            
        except Exception as e:
            logger.error(f"Error saving graph record: {e}")
            return {
                "success": False,
                "error": f"Failed to save graph: {str(e)}"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        try:
            # Check if graphs directory is accessible
            graphs_accessible = self.graphs_dir.exists() and self.graphs_dir.is_dir()
            
            # Check sub-services
            generation_healthy = self.generation_service is not None
            clustering_healthy = self.clustering_service is not None
            
            return {
                "success": True,
                "status": "healthy",
                "services": {
                    "generation": "healthy" if generation_healthy else "unhealthy",
                    "clustering": "healthy" if clustering_healthy else "unhealthy"
                },
                "storage": {
                    "graphs_directory": "accessible" if graphs_accessible else "inaccessible",
                    "graphs_dir_path": str(self.graphs_dir)
                }
            }
        except Exception as e:
            logger.error(f"Graph service health check failed: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            }