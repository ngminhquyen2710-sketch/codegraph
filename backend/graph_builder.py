"""
Graph Builder Module - Integrates with CodeFuse-CGM to build code graphs from repositories
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List
import networkx as nx

# Add parent directory to path to import CodeFuse-CGM modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from retriever.codegraph_parser.python.codegraph_python_local import parse, NodeType, EdgeType


class GraphBuilder:
    """
    Builds code graphs from repositories using CodeFuse-CGM components
    """
    
    def __init__(self, temp_dir: str = "./temp_repos"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def build_graph_from_repo(self, repo_path: str) -> Dict:
        """
        Build a code graph from a repository path
        This integrates with CodeFuse-CGM's graph generation
        """
        # For Python repositories, we can use the existing CodeFuse-CGM parser
        # For now, we'll use a simplified approach that scans Python files
        
        repo_name = Path(repo_path).name
        graph_data = self._scan_python_repository(repo_path, repo_name)
        
        return graph_data
    
    def _scan_python_repository(self, repo_path: str, repo_name: str) -> Dict:
        """
        Scan a Python repository and build a code graph
        This is a simplified version - full integration would use CodeFuse-CGM's graph generator
        """
        import traceback
        
        nodes = []
        edges = []
        node_id_counter = 0
        
        # Add repo node
        repo_id = f"node_{node_id_counter}"
        node_id_counter += 1
        nodes.append({
            "id": repo_id,
            "type": "repo",
            "label": repo_name,
            "data": {"name": repo_name, "path": repo_path}
        })
        
        # Scan for Python files
        try:
            python_files = list(Path(repo_path).rglob("*.py"))
            print(f"Found {len(python_files)} Python files")
        except Exception as e:
            print(f"Error scanning for Python files: {e}")
            traceback.print_exc()
            # Return minimal graph with just repo node
            return {
                "nodes": nodes,
                "edges": edges,
                "repo_name": repo_name
            }
        
        # Limit to first 50 files for performance in demo
        python_files = python_files[:50]
        
        if not python_files:
            print("No Python files found in repository")
            return {
                "nodes": nodes,
                "edges": edges,
                "repo_name": repo_name
            }
        
        file_nodes = {}
        
        print(f"Processing {len(python_files)} Python files...")
        
        for py_file in python_files:
            # Skip test files and __pycache__
            if 'test' in py_file.name.lower() or '__pycache__' in str(py_file):
                continue
                
            relative_path = str(py_file.relative_to(repo_path))
                
            file_id = f"node_{node_id_counter}"
            node_id_counter += 1
            
            file_node = {
                "id": file_id,
                "type": "file",
                "label": py_file.name,
                "data": {
                    "path": relative_path,
                    "name": py_file.name,
                    "full_path": str(py_file)
                }
            }
            nodes.append(file_node)
            file_nodes[relative_path] = file_id
            
            # Edge from repo to file
            edges.append({
                "source": repo_id,
                "target": file_id,
                "type": "contains",
                "label": "contains"
            })
            
            # Parse the Python file to extract classes and functions
            try:
                classes, functions = self._parse_python_file(py_file)
                
                # Map class names to their node IDs in this file
                class_name_to_id = {}
                
                for class_name in classes:
                    class_id = f"node_{node_id_counter}"
                    node_id_counter += 1
                    
                    nodes.append({
                        "id": class_id,
                        "type": "class",
                        "label": class_name,
                        "data": {
                            "name": class_name,
                            "file": relative_path
                        }
                    })
                    class_name_to_id[class_name] = class_id
                    
                    edges.append({
                        "source": file_id,
                        "target": class_id,
                        "type": "contains",
                        "label": "contains"
                    })
                
                for func_name, func_class in functions:
                    func_id = f"node_{node_id_counter}"
                    node_id_counter += 1
                    
                    nodes.append({
                        "id": func_id,
                        "type": "function",
                        "label": func_name,
                        "data": {
                            "name": func_name,
                            "class": func_class,
                            "file": relative_path
                        }
                    })
                    
                    if func_class and func_class in class_name_to_id:
                        # Connect to class if it belongs to one
                        edges.append({
                            "source": class_name_to_id[func_class],
                            "target": func_id,
                            "type": "contains",
                            "label": "contains"
                        })
                    else:
                        # Module-level function, connect to file
                        edges.append({
                            "source": file_id,
                            "target": func_id,
                            "type": "contains",
                            "label": "contains"
                        })
                        
            except Exception as e:
                print(f"Error parsing {py_file}: {e}")
                continue
        
        # Add import relationships between files
        try:
            self._add_import_relationships(nodes, edges, file_nodes, repo_path)
        except Exception as e:
            print(f"Error adding import relationships: {e}")
        
        print(f"Built graph with {len(nodes)} nodes and {len(edges)} edges")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "repo_name": repo_name
        }
    
    def _add_edge_with_aggregation(self, edges_dict: dict, source_id: str, target_id: str, edge_type: str):
        """
        Add edge with aggregation - merge duplicate edges and collect types
        """
        edge_key = (source_id, target_id)
        
        if edge_key not in edges_dict:
            edges_dict[edge_key] = {
                "source": source_id,
                "target": target_id,
                "type": edge_type,
                "label": edge_type,
                "types": [edge_type]  # Store all edge types
            }
        else:
            # Edge already exists, aggregate the type
            existing_edge = edges_dict[edge_key]
            if edge_type not in existing_edge["types"]:
                existing_edge["types"].append(edge_type)
                # Update label to show multiple types if needed
                if len(existing_edge["types"]) > 1:
                    existing_edge["label"] = ", ".join(existing_edge["types"])
                    existing_edge["type"] = "multi"  # Mark as multi-type edge
    
    def _convert_edge_dict_to_list(self, edges_dict: dict) -> list:
        """
        Convert edge dictionary to list, handling multi-type edges
        """
        edges = []
        for edge_key, edge_data in edges_dict.items():
            if len(edge_data["types"]) == 1:
                # Single type edge - keep simple format
                edges.append({
                    "source": edge_data["source"],
                    "target": edge_data["target"],
                    "type": edge_data["types"][0],
                    "label": edge_data["types"][0]
                })
            else:
                # Multi-type edge - include all types
                edges.append({
                    "source": edge_data["source"],
                    "target": edge_data["target"],
                    "type": "multi",
                    "label": ", ".join(edge_data["types"]),
                    "types": edge_data["types"]  # Keep all types for reference
                })
        return edges
    
    def _parse_python_file(self, file_path: Path) -> tuple:
        """
        Parse a Python file to extract classes and functions
        Returns: (classes_list, functions_list) where functions_list contains (name, class) tuples
        """
        import ast
        
        classes = []
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # First pass: collect all top-level classes and their methods
            class_stack = []
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    # Add methods of this class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            functions.append((item.name, node.name))
                elif isinstance(node, ast.FunctionDef):
                    # Module-level function
                    functions.append((node.name, None))
                    
        except Exception as e:
            print(f"AST parsing error for {file_path}: {e}")
        
        return classes, functions
    
    def _add_import_relationships(self, nodes: List, edges: List, file_nodes: Dict, repo_path: Path):
        """
        Add import relationships between files based on their content
        """
        import re
        
        # Build a mapping of file paths to node IDs
        path_to_id = {}
        for node in nodes:
            if node["type"] == "file":
                path_to_id[node["data"]["path"]] = node["id"]
        
        # Analyze imports in each file
        for node in nodes:
            if node["type"] == "file":
                file_path = Path(repo_path) / node["data"]["path"]
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Find import statements
                    import_pattern = r'^from\s+(\S+)\s+import|^import\s+(\S+)'
                    imports = re.findall(import_pattern, content, re.MULTILINE)
                    
                    for imp in imports:
                        imported_module = imp[0] if imp[0] else imp[1]
                        
                        # Try to find if this import refers to another file in the repo
                        for file_path_str, file_id in file_nodes.items():
                            if imported_module in file_path_str or file_path_str.endswith(f"{imported_module.replace('.', '/')}.py"):
                                # Add import edge
                                if node["id"] != file_id:  # Don't import from self
                                    edges.append({
                                        "source": node["id"],
                                        "target": file_id,
                                        "type": "imports",
                                        "label": "imports"
                                    })
                                    break
                                    
                except Exception as e:
                    continue


def build_graph_for_repo(repo_path: str) -> Dict:
    """
    Convenience function to build a graph for a repository
    """
    builder = GraphBuilder()
    return builder.build_graph_from_repo(repo_path)
