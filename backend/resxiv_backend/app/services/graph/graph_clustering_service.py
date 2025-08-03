"""
Graph Clustering Service - L6 Engineering Standards
Focused on ML-based clustering algorithms and cluster analysis.
"""

import uuid
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class GraphClusteringService:
    """
    Clustering service for graph analysis.
    Single Responsibility: ML-based clustering algorithms and analysis.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @handle_service_errors("perform clustering analysis")
    async def perform_clustering_analysis(
        self,
        papers_data: List[Dict[str, Any]],
        clustering_algorithm: str = "auto",
        n_clusters: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform clustering analysis on papers based on embeddings.
        
        Args:
            papers_data: Papers with embeddings
            clustering_algorithm: Algorithm choice
            n_clusters: Number of clusters (for algorithms that require it)
            
        Returns:
            Clustering analysis result
        """
        try:
            if len(papers_data) < 3:
                return {
                    "success": False,
                    "error": "Insufficient papers for clustering analysis",
                    "minimum_required": 3
                }
            
            # Extract embeddings
            embeddings = np.array([paper["embedding"] for paper in papers_data])
            
            # Determine optimal clustering parameters
            if clustering_algorithm == "auto":
                algorithm_result = await self._select_optimal_algorithm(embeddings)
                clustering_algorithm = algorithm_result["algorithm"]
                optimal_params = algorithm_result["parameters"]
            else:
                optimal_params = await self._get_algorithm_parameters(
                    clustering_algorithm, embeddings, n_clusters
                )
            
            # Perform clustering
            cluster_result = await self._apply_clustering_algorithm(
                embeddings, clustering_algorithm, optimal_params
            )
            
            if not cluster_result["success"]:
                return cluster_result
            
            # Analyze clusters
            cluster_analysis = await self._analyze_clusters(
                papers_data, cluster_result["labels"], embeddings
            )
            
            # Generate cluster visualization data
            viz_data = await self._generate_cluster_visualization(
                embeddings, cluster_result["labels"], papers_data
            )
            
            return {
                "success": True,
                "algorithm_used": clustering_algorithm,
                "parameters": optimal_params,
                "cluster_labels": cluster_result["labels"].tolist(),
                "cluster_analysis": cluster_analysis,
                "visualization": viz_data,
                "quality_metrics": cluster_result.get("quality_metrics", {})
            }
            
        except Exception as e:
            logger.error(f"Error in clustering analysis: {e}")
            raise ServiceError(
                f"Clustering analysis failed: {str(e)}",
                ErrorCodes.ANALYSIS_ERROR
            )
    
    async def _select_optimal_algorithm(self, embeddings: np.ndarray) -> Dict[str, Any]:
        """
        Select optimal clustering algorithm based on data characteristics.
        
        Args:
            embeddings: Paper embeddings
            
        Returns:
            Optimal algorithm and parameters
        """
        try:
            n_samples = len(embeddings)
            
            # Test different algorithms and select best
            algorithms_to_test = []
            
            # K-means (good for spherical clusters)
            if n_samples >= 8:
                algorithms_to_test.append({
                    "algorithm": "kmeans",
                    "params": {"n_clusters": min(max(2, n_samples // 4), 8)}
                })
            
            # DBSCAN (good for arbitrary shapes)
            algorithms_to_test.append({
                "algorithm": "dbscan",
                "params": {"eps": 0.3, "min_samples": max(2, min(3, n_samples // 3))}
            })
            
            # Hierarchical (good for nested structures)
            if n_samples >= 4:
                algorithms_to_test.append({
                    "algorithm": "hierarchical",
                    "params": {"n_clusters": min(max(2, n_samples // 3), 6)}
                })
            
            best_score = -1
            best_algorithm = "dbscan"
            best_params = {"eps": 0.3, "min_samples": 2}
            
            for test in algorithms_to_test:
                try:
                    result = await self._apply_clustering_algorithm(
                        embeddings, test["algorithm"], test["params"]
                    )
                    
                    if result["success"] and "silhouette_score" in result["quality_metrics"]:
                        score = result["quality_metrics"]["silhouette_score"]
                        if score > best_score:
                            best_score = score
                            best_algorithm = test["algorithm"]
                            best_params = test["params"]
                except Exception:
                    continue
            
            return {
                "algorithm": best_algorithm,
                "parameters": best_params,
                "selection_score": best_score
            }
            
        except Exception as e:
            logger.warning(f"Error in algorithm selection, using default: {e}")
            return {
                "algorithm": "dbscan",
                "parameters": {"eps": 0.3, "min_samples": 2}
            }
    
    async def _get_algorithm_parameters(
        self,
        algorithm: str,
        embeddings: np.ndarray,
        n_clusters: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get optimal parameters for specified algorithm.
        
        Args:
            algorithm: Clustering algorithm
            embeddings: Paper embeddings
            n_clusters: Desired number of clusters
            
        Returns:
            Algorithm parameters
        """
        n_samples = len(embeddings)
        
        if algorithm == "kmeans":
            optimal_k = n_clusters or min(max(2, n_samples // 4), 8)
            return {"n_clusters": optimal_k, "random_state": 42}
        
        elif algorithm == "dbscan":
            # Estimate eps using k-distance graph
            from sklearn.neighbors import NearestNeighbors
            k = min(4, n_samples - 1)
            neighbors = NearestNeighbors(n_neighbors=k)
            neighbors.fit(embeddings)
            distances, _ = neighbors.kneighbors(embeddings)
            eps = np.mean(distances[:, -1])
            
            return {
                "eps": eps,
                "min_samples": max(2, min(3, n_samples // 5))
            }
        
        elif algorithm == "hierarchical":
            optimal_clusters = n_clusters or min(max(2, n_samples // 3), 6)
            return {"n_clusters": optimal_clusters, "linkage": "ward"}
        
        else:
            return {}
    
    async def _apply_clustering_algorithm(
        self,
        embeddings: np.ndarray,
        algorithm: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply clustering algorithm with given parameters.
        
        Args:
            embeddings: Paper embeddings
            algorithm: Algorithm name
            parameters: Algorithm parameters
            
        Returns:
            Clustering result
        """
        try:
            if algorithm == "kmeans":
                clusterer = KMeans(**parameters)
                labels = clusterer.fit_predict(embeddings)
                
            elif algorithm == "dbscan":
                clusterer = DBSCAN(**parameters)
                labels = clusterer.fit_predict(embeddings)
                
            elif algorithm == "hierarchical":
                clusterer = AgglomerativeClustering(**parameters)
                labels = clusterer.fit_predict(embeddings)
                
            else:
                raise ValueError(f"Unsupported clustering algorithm: {algorithm}")
            
            # Calculate quality metrics
            quality_metrics = {}
            
            # Silhouette score (if more than 1 cluster and not all noise)
            unique_labels = np.unique(labels)
            if len(unique_labels) > 1 and not (len(unique_labels) == 1 and unique_labels[0] == -1):
                try:
                    silhouette = silhouette_score(embeddings, labels)
                    quality_metrics["silhouette_score"] = float(silhouette)
                except Exception:
                    pass
            
            # Cluster distribution
            unique, counts = np.unique(labels, return_counts=True)
            quality_metrics["cluster_distribution"] = {
                str(label): int(count) for label, count in zip(unique, counts)
            }
            quality_metrics["number_of_clusters"] = len(unique_labels)
            
            # Noise points (for DBSCAN)
            if algorithm == "dbscan":
                noise_points = np.sum(labels == -1)
                quality_metrics["noise_points"] = int(noise_points)
                quality_metrics["noise_ratio"] = float(noise_points / len(labels))
            
            return {
                "success": True,
                "labels": labels,
                "quality_metrics": quality_metrics
            }
            
        except Exception as e:
            logger.error(f"Error applying {algorithm} clustering: {e}")
            return {
                "success": False,
                "error": f"Failed to apply {algorithm} clustering: {str(e)}"
            }
    
    async def _analyze_clusters(
        self,
        papers_data: List[Dict[str, Any]],
        labels: np.ndarray,
        embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """
        Analyze cluster characteristics and topics.
        
        Args:
            papers_data: Papers data
            labels: Cluster labels
            embeddings: Paper embeddings
            
        Returns:
            Cluster analysis
        """
        try:
            clusters = {}
            unique_labels = np.unique(labels)
            
            for label in unique_labels:
                cluster_indices = np.where(labels == label)[0]
                cluster_papers = [papers_data[i] for i in cluster_indices]
                cluster_embeddings = embeddings[cluster_indices]
                
                # Calculate cluster centroid
                centroid = np.mean(cluster_embeddings, axis=0)
                
                # Calculate intra-cluster similarity
                if len(cluster_embeddings) > 1:
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarities = cosine_similarity(cluster_embeddings)
                    # Average similarity excluding diagonal
                    mask = ~np.eye(similarities.shape[0], dtype=bool)
                    avg_similarity = np.mean(similarities[mask])
                else:
                    avg_similarity = 1.0
                
                # Extract common keywords and topics
                all_keywords = []
                for paper in cluster_papers:
                    if paper.get("keywords"):
                        all_keywords.extend(paper["keywords"])
                
                # Count keyword frequency
                keyword_counts = {}
                for keyword in all_keywords:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                
                # Get most common keywords
                sorted_keywords = sorted(
                    keyword_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                cluster_info = {
                    "label": int(label),
                    "size": len(cluster_papers),
                    "papers": [
                        {
                            "id": paper["id"],
                            "title": paper["title"],
                            "authors": paper["authors"]
                        }
                        for paper in cluster_papers
                    ],
                    "characteristics": {
                        "avg_intra_similarity": float(avg_similarity),
                        "common_keywords": [
                            {"keyword": kw, "frequency": count}
                            for kw, count in sorted_keywords
                        ],
                        "centroid_norm": float(np.linalg.norm(centroid))
                    }
                }
                
                clusters[str(label)] = cluster_info
            
            return {
                "clusters": clusters,
                "summary": {
                    "total_clusters": len(unique_labels),
                    "largest_cluster_size": max(
                        cluster["size"] for cluster in clusters.values()
                    ) if clusters else 0,
                    "smallest_cluster_size": min(
                        cluster["size"] for cluster in clusters.values()
                    ) if clusters else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing clusters: {e}")
            return {
                "error": f"Failed to analyze clusters: {str(e)}",
                "clusters": {}
            }
    
    async def _generate_cluster_visualization(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        papers_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate visualization data for clusters.
        
        Args:
            embeddings: Paper embeddings
            labels: Cluster labels
            papers_data: Papers data
            
        Returns:
            Visualization data
        """
        try:
            # Reduce dimensionality for visualization
            if embeddings.shape[1] > 2:
                pca = PCA(n_components=2, random_state=42)
                reduced_embeddings = pca.fit_transform(embeddings)
                explained_variance = pca.explained_variance_ratio_
            else:
                reduced_embeddings = embeddings
                explained_variance = [1.0, 0.0]
            
            # Create visualization points
            points = []
            for i, (paper, embedding_2d, label) in enumerate(
                zip(papers_data, reduced_embeddings, labels)
            ):
                point = {
                    "id": paper["id"],
                    "title": paper["title"],
                    "x": float(embedding_2d[0]),
                    "y": float(embedding_2d[1]),
                    "cluster": int(label),
                    "authors": paper["authors"][:3] if len(paper["authors"]) > 3 else paper["authors"]
                }
                points.append(point)
            
            return {
                "points": points,
                "dimensionality_reduction": {
                    "method": "PCA",
                    "explained_variance_ratio": explained_variance.tolist(),
                    "total_explained_variance": float(np.sum(explained_variance))
                },
                "layout_algorithm": "scatter",
                "color_scheme": "cluster_based"
            }
            
        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            return {
                "error": f"Failed to generate visualization: {str(e)}",
                "points": []
            } 