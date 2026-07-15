"""
Embedding Index Module - Generates and stores embeddings for code graph nodes
"""
import os
import pickle
import numpy as np
import faiss
from typing import Dict, List
from pathlib import Path


class EmbeddingIndex:
    """
    Manages embeddings for code graph nodes using FAISS
    """
    
    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
        self.index = None
        self.node_id_to_idx = {}
        self.idx_to_node_id = {}
        self.embeddings = {}
    
    def build_index(self, graph_data: Dict):
        """
        Build FAISS index from graph nodes
        """
        nodes = graph_data["nodes"]
        
        # For demo, generate random embeddings
        # In production, this would use CodeFuse-CGE or similar
        embeddings_list = []
        
        for idx, node in enumerate(nodes):
            # Generate a simple embedding based on node type and label
            embedding = self._generate_simple_embedding(node)
            embeddings_list.append(embedding)
            
            self.node_id_to_idx[node["id"]] = idx
            self.idx_to_node_id[idx] = node["id"]
            self.embeddings[node["id"]] = embedding
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings_list).astype('float32')
        
        # Build FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(embeddings_array)
        
        return len(nodes)
    
    def _generate_simple_embedding(self, node: Dict) -> np.ndarray:
        """
        Generate a simple embedding for a node (placeholder)
        In production, this would use CodeFuse-CGE or similar
        """
        # Create a simple hash-based embedding
        node_str = f"{node['type']}_{node.get('label', '')}_{node.get('data', {})}"
        
        # Generate a deterministic embedding based on the string
        hash_val = hash(node_str)
        np.random.seed(hash_val % (2**32))
        embedding = np.random.randn(self.embedding_dim).astype('float32')
        
        return embedding
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[tuple]:
        """
        Search for similar nodes
        Returns list of (node_id, distance) tuples
        """
        if self.index is None:
            return []
        
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx in self.idx_to_node_id:
                node_id = self.idx_to_node_id[idx]
                results.append((node_id, float(dist)))
        
        return results
    
    def save(self, path: str):
        """
        Save the index to disk
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'index': self.index,
                'node_id_to_idx': self.node_id_to_idx,
                'idx_to_node_id': self.idx_to_node_id,
                'embeddings': self.embeddings,
                'embedding_dim': self.embedding_dim
            }, f)
    
    def load(self, path: str):
        """
        Load the index from disk
        """
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.index = data['index']
        self.node_id_to_idx = data['node_id_to_idx']
        self.idx_to_node_id = data['idx_to_node_id']
        self.embeddings = data['embeddings']
        self.embedding_dim = data['embedding_dim']


class GraphDatabase:
    """
    Simple in-memory graph database using NetworkX
    In production, this could be replaced with Neo4j or similar
    """
    
    def __init__(self):
        import networkx as nx
        self.graph = nx.DiGraph()
        self.node_data = {}
    
    def add_graph(self, graph_data: Dict):
        """
        Add a code graph to the database
        """
        nodes = graph_data["nodes"]
        edges = graph_data["edges"]
        
        # Add nodes
        for node in nodes:
            self.graph.add_node(node["id"], **node["data"])
            self.node_data[node["id"]] = node
        
        # Add edges
        for edge in edges:
            self.graph.add_edge(
                edge["source"],
                edge["target"],
                edge_type=edge["type"],
                label=edge.get("label", "")
            )
    
    def get_node(self, node_id: str) -> Dict:
        """
        Get node data by ID
        """
        return self.node_data.get(node_id)
    
    def get_neighbors(self, node_id: str, edge_type: str = None) -> List[Dict]:
        """
        Get neighboring nodes
        """
        if node_id not in self.graph:
            return []
        
        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)
            
            if edge_type is None or edge_data.get("edge_type") == edge_type:
                neighbors.append(self.node_data.get(neighbor))
        
        return neighbors
    
    def get_subgraph(self, node_ids: List[str], depth: int = 1) -> Dict:
        """
        Extract a subgraph around the given nodes
        """
        subgraph_nodes = set(node_ids)
        
        # Expand to neighbors
        for _ in range(depth):
            new_nodes = set()
            for node_id in subgraph_nodes:
                neighbors = list(self.graph.neighbors(node_id))
                new_nodes.update(neighbors)
            subgraph_nodes.update(new_nodes)
        
        # Extract nodes and edges
        nodes = [self.node_data[nid] for nid in subgraph_nodes if nid in self.node_data]
        edges = []
        
        for node_id in subgraph_nodes:
            for neighbor in self.graph.neighbors(node_id):
                if neighbor in subgraph_nodes:
                    edge_data = self.graph.get_edge_data(node_id, neighbor)
                    edges.append({
                        "source": node_id,
                        "target": neighbor,
                        "type": edge_data.get("edge_type", "unknown"),
                        "label": edge_data.get("label", "")
                    })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def search_by_type(self, node_type: str) -> List[Dict]:
        """
        Search for nodes by type
        """
        results = []
        for node_id, node in self.node_data.items():
            if node.get("type") == node_type:
                results.append(node)
        return results
    
    def search_by_name(self, name: str) -> List[Dict]:
        """
        Search for nodes by name (fuzzy match)
        """
        from rapidfuzz import process, fuzz
        
        node_names = [(nid, node.get("label", node.get("data", {}).get("name", ""))) 
                      for nid, node in self.node_data.items()]
        
        matches = process.extract(name, [(nid, name) for nid, name in node_names], 
                                  scorer=fuzz.WRatio, limit=10)
        
        results = []
        for match in matches:
            node_id = match[0][0]
            results.append(self.node_data[node_id])
        
        return results


def create_embedding_index(graph_data: Dict) -> EmbeddingIndex:
    """
    Convenience function to create an embedding index
    """
    index = EmbeddingIndex()
    index.build_index(graph_data)
    return index


def create_graph_database(graph_data: Dict) -> GraphDatabase:
    """
    Convenience function to create a graph database
    """
    db = GraphDatabase()
    db.add_graph(graph_data)
    return db
