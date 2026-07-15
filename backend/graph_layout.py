"""
Graph layout algorithms for hierarchical visualization
Implements clustering by package/module and Sugiyama layered layout
"""
import networkx as nx
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class GraphLayout:
    """
    Handles graph clustering and hierarchical layout
    """
    
    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        self.nodes = nodes
        self.edges = edges
        self.graph = self._build_graph()
        
    def _build_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from nodes and edges"""
        G = nx.DiGraph()
        
        # Add nodes
        for node in self.nodes:
            G.add_node(node['id'], **node)
        
        # Add edges
        for edge in self.edges:
            G.add_edge(edge['source'], edge['target'], **edge)
        
        return G
    
    def cluster_by_package(self) -> Dict[str, List[Dict]]:
        """
        Cluster nodes by package/module based on file paths
        Returns a dictionary mapping cluster names to node lists
        """
        clusters = defaultdict(list)
        
        for node in self.nodes:
            # Extract package/module from node data
            if node.get('type') == 'file':
                path = node.get('data', {}).get('path', '')
                # Get directory path as cluster name
                if '/' in path:
                    cluster_name = '/'.join(path.split('/')[:-1])
                elif '\\' in path:
                    cluster_name = '\\'.join(path.split('\\')[:-1])
                else:
                    cluster_name = 'root'
            elif node.get('type') in ['class', 'function']:
                # Use file path for class/function nodes
                file_path = node.get('data', {}).get('file', '')
                if '/' in file_path:
                    cluster_name = '/'.join(file_path.split('/')[:-1])
                elif '\\' in file_path:
                    cluster_name = '\\'.join(file_path.split('\\')[:-1])
                else:
                    cluster_name = 'root'
            else:
                cluster_name = 'root'
            
            clusters[cluster_name].append(node)
        
        return dict(clusters)
    
    def create_cluster_graph(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Create a clustered view where each cluster is a super-node
        Returns (cluster_nodes, cluster_edges)
        """
        clusters = self.cluster_by_package()
        cluster_nodes = []
        cluster_edges = []
        
        # Create cluster nodes
        cluster_id_map = {}
        for idx, (cluster_name, nodes_in_cluster) in enumerate(clusters.items()):
            cluster_id = f"cluster_{idx}"
            cluster_id_map[cluster_name] = cluster_id
            
            cluster_nodes.append({
                'id': cluster_id,
                'type': 'cluster',
                'label': cluster_name,
                'data': {
                    'name': cluster_name,
                    'node_count': len(nodes_in_cluster),
                    'nodes': nodes_in_cluster
                }
            })
        
        # Create cluster edges based on inter-cluster connections
        cluster_connections = defaultdict(set)
        for edge in self.edges:
            source_cluster = self._get_node_cluster(edge['source'], clusters)
            target_cluster = self._get_node_cluster(edge['target'], clusters)
            
            if source_cluster != target_cluster:
                source_cluster_id = cluster_id_map[source_cluster]
                target_cluster_id = cluster_id_map[target_cluster]
                cluster_connections[(source_cluster_id, target_cluster_id)].add(edge['type'])
        
        # Create edges between clusters
        for (source, target), edge_types in cluster_connections.items():
            cluster_edges.append({
                'source': source,
                'target': target,
                'type': ','.join(edge_types),
                'data': {
                    'edge_count': len(edge_types)
                }
            })
        
        return cluster_nodes, cluster_edges
    
    def _get_node_cluster(self, node_id: str, clusters: Dict[str, List[Dict]]) -> str:
        """Get cluster name for a node"""
        for cluster_name, nodes_in_cluster in clusters.items():
            if any(node['id'] == node_id for node in nodes_in_cluster):
                return cluster_name
        return 'root'
    
    def sugiyama_layout(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Tuple[float, float]]:
        """
        Implement simplified Sugiyama layered layout algorithm
        Returns a dictionary mapping node IDs to (x, y) positions
        """
        G = nx.DiGraph()
        
        # Add nodes
        for node in nodes:
            G.add_node(node['id'])
        
        # Add edges
        for edge in edges:
            G.add_edge(edge['source'], edge['target'])
        
        # Use NetworkX's layered layout (simplified Sugiyama)
        # This is a basic implementation - for production, consider using ELK or Dagre
        try:
            # Try to use networkx's multipartite_layout (layered)
            layers = self._assign_layers(G)
            pos = nx.multipartite_layout(G, subset_key='layer')
            
            # Scale positions
            max_x = max(p[0] for p in pos.values()) if pos else 1
            max_y = max(p[1] for p in pos.values()) if pos else 1
            
            scaled_pos = {}
            for node_id, (x, y) in pos.items():
                scaled_pos[node_id] = (
                    (x / max_x) * 800 + 50,  # Scale x to 0-800 range
                    (y / max_y) * 600 + 50   # Scale y to 0-600 range
                )
            
            return scaled_pos
        except Exception as e:
            print(f"Error in sugiyama layout: {e}")
            # Fallback to random layout
            pos = nx.spring_layout(G, k=2, iterations=50)
            scaled_pos = {}
            for node_id, (x, y) in pos.items():
                scaled_pos[node_id] = (
                    (x + 1) * 400 + 50,
                    (y + 1) * 300 + 50
                )
            return scaled_pos
    
    def _assign_layers(self, G: nx.DiGraph) -> Dict[str, int]:
        """
        Assign layers to nodes for Sugiyama layout
        Uses longest path layering
        """
        # Get topological order
        try:
            topo_order = list(nx.topological_sort(G))
        except nx.NetworkXError:
            # Graph has cycles, use DFS order
            topo_order = list(G.nodes())
        
        # Assign layers based on longest path from source
        layers = {}
        for node in topo_order:
            # Get max layer of predecessors
            pred_layers = [layers[pred] for pred in G.predecessors(node) if pred in layers]
            if pred_layers:
                layers[node] = max(pred_layers) + 1
            else:
                layers[node] = 0
        
        # Add layer attribute to graph
        for node, layer in layers.items():
            G.nodes[node]['layer'] = layer
        
        return layers
    
    def get_cluster_contents(self, cluster_name: str) -> List[Dict]:
        """
        Get all nodes in a specific cluster
        """
        clusters = self.cluster_by_package()
        return clusters.get(cluster_name, [])
    
    def get_cluster_subgraph(self, cluster_name: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Get nodes and edges within a specific cluster
        """
        clusters = self.cluster_by_package()
        nodes_in_cluster = clusters.get(cluster_name, [])
        node_ids = {node['id'] for node in nodes_in_cluster}
        
        # Get edges within cluster
        edges_in_cluster = [
            edge for edge in self.edges
            if edge['source'] in node_ids and edge['target'] in node_ids
        ]
        
        return nodes_in_cluster, edges_in_cluster


def create_graph_layout(nodes: List[Dict], edges: List[Dict]) -> GraphLayout:
    """
    Convenience function to create a GraphLayout instance
    """
    return GraphLayout(nodes, edges)
