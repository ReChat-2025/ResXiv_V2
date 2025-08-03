"""
Graph Generation Service - L6 Engineering Standards
Focused on core graph creation and adjacency matrix building.
"""

import uuid
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.metrics.pairwise import cosine_similarity

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.paper_repository import PaperRepository
from app.services.paper.paper_embedding_service import PaperEmbeddingService
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GraphGenerationService:
    """
    Graph generation service for paper networks.
    Single Responsibility: Core graph creation and adjacency matrix operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.paper_repository = PaperRepository(session)
        self.embedding_service = PaperEmbeddingService(session)
        self.graphs_dir = settings.files.static_dir / "graphs"
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
    
    @handle_service_errors("generate project graph")
    async def generate_project_graph(
        self,
        project_id: uuid.UUID,
        similarity_threshold: float = 0.7,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate paper graph for a project based on embedding similarity.
        
        Args:
            project_id: Project UUID
            similarity_threshold: Minimum similarity for edge connection
            force_regenerate: Whether to force regeneration
            
        Returns:
            Graph generation result
        """
        try:
            logger.info(f"Generating paper graph for project: {project_id}")
            
            # Get papers with embeddings for the project
            papers_data = await self._get_project_papers_with_embeddings(project_id)
            
            if len(papers_data) < 2:
                return {
                    "success": False,
                    "error": "Insufficient papers with embeddings for graph generation",
                    "papers_count": len(papers_data),
                    "minimum_required": 2
                }
            
            # Generate adjacency matrix
            adjacency_result = await self._generate_adjacency_matrix(
                papers_data, similarity_threshold
            )
            
            if not adjacency_result["success"]:
                return adjacency_result
            
            # Create graph structure
            graph_data = await self._create_graph_structure(
                papers_data, 
                adjacency_result["adjacency_matrix"],
                adjacency_result["similarity_matrix"],
                similarity_threshold
            )
            
            # Calculate graph metrics
            metrics = await self._calculate_graph_metrics(
                graph_data["nodes"],
                graph_data["edges"],
                adjacency_result["adjacency_matrix"]
            )
            
            result = {
                "success": True,
                "project_id": str(project_id),
                "graph": graph_data,
                "metrics": metrics,
                "parameters": {
                    "similarity_threshold": similarity_threshold,
                    "papers_count": len(papers_data),
                    "edges_count": len(graph_data["edges"])
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating project graph: {e}")
            raise ServiceError(
                f"Failed to generate project graph: {str(e)}",
                ErrorCodes.GENERATION_ERROR
            )
    
    async def _get_project_papers_with_embeddings(
        self, 
        project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get papers for project that have embeddings available.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of papers with embeddings
        """
        try:
            # Get papers from project
            papers = await self.paper_repository.get_papers_by_project(project_id)
            
            papers_with_embeddings = []
            
            for paper in papers:
                # Check if paper has embeddings
                embedding = await self.embedding_service.get_paper_embedding(paper.id)
                
                if embedding and len(embedding) > 0:
                    papers_with_embeddings.append({
                        "id": str(paper.id),
                        "title": paper.title,
                        "authors": paper.authors,
                        "abstract": paper.abstract,
                        "keywords": paper.keywords,
                        "embedding": np.array(embedding),
                        "created_at": paper.created_at.isoformat() if paper.created_at else None,
                        "metadata": {
                            "file_type": paper.file_type,
                            "file_size": paper.file_size,
                            "doi": paper.doi,
                            "arxiv_id": paper.arxiv_id
                        }
                    })
            
            logger.info(f"Found {len(papers_with_embeddings)} papers with embeddings for project {project_id}")
            return papers_with_embeddings
            
        except Exception as e:
            logger.error(f"Error getting papers with embeddings: {e}")
            raise ServiceError(
                f"Failed to get papers with embeddings: {str(e)}",
                ErrorCodes.FETCH_ERROR
            )
    
    async def _generate_adjacency_matrix(
        self,
        papers_data: List[Dict[str, Any]],
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """
        Generate adjacency matrix based on embedding similarity.
        
        Args:
            papers_data: List of papers with embeddings
            similarity_threshold: Minimum similarity for connection
            
        Returns:
            Adjacency matrix generation result
        """
        try:
            # Extract embeddings
            embeddings = np.array([paper["embedding"] for paper in papers_data])
            
            # Calculate cosine similarity matrix
            similarity_matrix = cosine_similarity(embeddings)
            
            # Create adjacency matrix based on threshold
            adjacency_matrix = (similarity_matrix >= similarity_threshold).astype(int)
            
            # Remove self-connections
            np.fill_diagonal(adjacency_matrix, 0)
            
            # Calculate metrics
            total_possible_edges = len(papers_data) * (len(papers_data) - 1) // 2
            actual_edges = np.sum(adjacency_matrix) // 2  # Divide by 2 for undirected graph
            density = actual_edges / total_possible_edges if total_possible_edges > 0 else 0
            
            return {
                "success": True,
                "adjacency_matrix": adjacency_matrix,
                "similarity_matrix": similarity_matrix,
                "metrics": {
                    "total_possible_edges": total_possible_edges,
                    "actual_edges": actual_edges,
                    "graph_density": density,
                    "average_similarity": float(np.mean(similarity_matrix[similarity_matrix != 1.0])),
                    "max_similarity": float(np.max(similarity_matrix[similarity_matrix != 1.0])),
                    "min_similarity": float(np.min(similarity_matrix[similarity_matrix != 1.0]))
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating adjacency matrix: {e}")
            return {
                "success": False,
                "error": f"Failed to generate adjacency matrix: {str(e)}"
            }
    
    async def _create_graph_structure(
        self,
        papers_data: List[Dict[str, Any]],
        adjacency_matrix: np.ndarray,
        similarity_matrix: np.ndarray,
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """
        Create graph structure with nodes and edges.
        
        Args:
            papers_data: Papers data
            adjacency_matrix: Adjacency matrix
            similarity_matrix: Similarity matrix
            similarity_threshold: Similarity threshold
            
        Returns:
            Graph structure
        """
        try:
            # Create nodes
            nodes = []
            for i, paper in enumerate(papers_data):
                node = {
                    "id": paper["id"],
                    "title": paper["title"],
                    "authors": paper["authors"],
                    "abstract": paper["abstract"][:200] + "..." if len(paper.get("abstract", "")) > 200 else paper.get("abstract", ""),
                    "keywords": paper.get("keywords", []),
                    "metadata": paper.get("metadata", {}),
                    "created_at": paper.get("created_at"),
                    "degree": int(np.sum(adjacency_matrix[i])),  # Number of connections
                    "position": {
                        "x": 0,  # Will be set by frontend layout algorithm
                        "y": 0
                    }
                }
                nodes.append(node)
            
            # Create edges
            edges = []
            for i in range(len(papers_data)):
                for j in range(i + 1, len(papers_data)):
                    if adjacency_matrix[i][j] == 1:
                        similarity_score = float(similarity_matrix[i][j])
                        edge = {
                            "source": papers_data[i]["id"],
                            "target": papers_data[j]["id"],
                            "weight": similarity_score,
                            "strength": min((similarity_score - similarity_threshold) / (1 - similarity_threshold), 1.0),
                            "type": "similarity"
                        }
                        edges.append(edge)
            
            return {
                "nodes": nodes,
                "edges": edges,
                "layout": "force-directed",  # Recommended layout algorithm
                "metadata": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "similarity_threshold": similarity_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating graph structure: {e}")
            raise ServiceError(
                f"Failed to create graph structure: {str(e)}",
                ErrorCodes.GENERATION_ERROR
            )
    
    async def _calculate_graph_metrics(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        adjacency_matrix: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculate graph topology metrics.
        
        Args:
            nodes: Graph nodes
            edges: Graph edges
            adjacency_matrix: Adjacency matrix
            
        Returns:
            Graph metrics
        """
        try:
            import networkx as nx
            from scipy.sparse.csgraph import connected_components
            
            # Create NetworkX graph for analysis
            G = nx.Graph()
            
            # Add nodes
            for node in nodes:
                G.add_node(node["id"], **node)
            
            # Add edges
            for edge in edges:
                G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
            
            # Calculate metrics
            metrics = {
                "basic_metrics": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "density": nx.density(G) if len(nodes) > 1 else 0,
                    "is_connected": nx.is_connected(G) if len(nodes) > 0 else False
                },
                "centrality_metrics": {},
                "clustering_metrics": {},
                "component_analysis": {}
            }
            
            if len(nodes) > 0:
                # Centrality metrics
                if len(edges) > 0:
                    degree_centrality = nx.degree_centrality(G)
                    betweenness_centrality = nx.betweenness_centrality(G)
                    closeness_centrality = nx.closeness_centrality(G)
                    
                    metrics["centrality_metrics"] = {
                        "average_degree_centrality": np.mean(list(degree_centrality.values())),
                        "max_degree_centrality": max(degree_centrality.values()),
                        "average_betweenness_centrality": np.mean(list(betweenness_centrality.values())),
                        "max_betweenness_centrality": max(betweenness_centrality.values()),
                        "average_closeness_centrality": np.mean(list(closeness_centrality.values())),
                        "max_closeness_centrality": max(closeness_centrality.values())
                    }
                
                # Clustering metrics
                if len(edges) > 0:
                    clustering_coefficient = nx.average_clustering(G)
                    transitivity = nx.transitivity(G)
                    
                    metrics["clustering_metrics"] = {
                        "average_clustering_coefficient": clustering_coefficient,
                        "transitivity": transitivity
                    }
                
                # Component analysis
                components = list(nx.connected_components(G))
                metrics["component_analysis"] = {
                    "number_of_components": len(components),
                    "largest_component_size": max(len(comp) for comp in components) if components else 0,
                    "component_sizes": [len(comp) for comp in components]
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating graph metrics: {e}")
            return {
                "error": f"Failed to calculate metrics: {str(e)}",
                "basic_metrics": {
                    "node_count": len(nodes),
                    "edge_count": len(edges)
                }
            }
    
    @handle_service_errors("regenerate graph")
    async def regenerate_project_graph(
        self,
        project_id: uuid.UUID,
        new_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Regenerate project graph with updated parameters.
        
        Args:
            project_id: Project UUID
            new_threshold: New similarity threshold
            
        Returns:
            Regeneration result
        """
        threshold = new_threshold or 0.7
        
        return await self.generate_project_graph(
            project_id=project_id,
            similarity_threshold=threshold,
            force_regenerate=True
        )
    
    @handle_service_errors("validate graph data")
    async def validate_graph_data(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate graph data structure and integrity.
        
        Args:
            graph_data: Graph data to validate
            
        Returns:
            Validation result
        """
        try:
            issues = []
            
            # Check required fields
            required_fields = ["nodes", "edges", "metadata"]
            for field in required_fields:
                if field not in graph_data:
                    issues.append(f"Missing required field: {field}")
            
            if "nodes" in graph_data:
                # Check node structure
                for i, node in enumerate(graph_data["nodes"]):
                    required_node_fields = ["id", "title"]
                    for field in required_node_fields:
                        if field not in node:
                            issues.append(f"Node {i} missing required field: {field}")
            
            if "edges" in graph_data:
                # Check edge structure and references
                node_ids = {node["id"] for node in graph_data.get("nodes", [])}
                for i, edge in enumerate(graph_data["edges"]):
                    if "source" not in edge or "target" not in edge:
                        issues.append(f"Edge {i} missing source or target")
                    elif edge["source"] not in node_ids or edge["target"] not in node_ids:
                        issues.append(f"Edge {i} references non-existent nodes")
            
            return {
                "success": len(issues) == 0,
                "issues": issues,
                "valid": len(issues) == 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "issues": [f"Validation error: {str(e)}"],
                "valid": False
            } 