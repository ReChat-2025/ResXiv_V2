"""
DEPRECATED: Legacy Graph Service - DO NOT USE

This file has been refactored into focused modules following L6 engineering standards:
- app/services/graph/graph_generation_service.py - Core graph creation and adjacency matrices
- app/services/graph/graph_clustering_service.py - ML-based clustering and analysis
- app/services/graph/graph_service_integrated.py - Orchestration layer

Please use the new GraphService from app.services.graph.graph_service_integrated

This file will be removed in the next version.
"""

import warnings
from app.services.graph.graph_service_integrated import GraphService as NewGraphService

warnings.warn(
    "graph_service.py is deprecated. Use app.services.graph.graph_service_integrated.GraphService instead",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility aliases - will be removed
GraphService = NewGraphService 