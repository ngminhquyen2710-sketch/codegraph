"""
FastAPI backend for CodeExplorer AI
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import os
import sys
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import CodeFuse-CGM modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from retriever.codegraph_parser.python.codegraph_python_local import parse, NodeType, EdgeType
import networkx as nx
from graph_builder import build_graph_for_repo
from embedding_index import create_embedding_index, create_graph_database
from graph_retriever import create_graph_retriever, create_llm_client
from graph_layout import create_graph_layout

app = FastAPI(title="CodeExplorer AI API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for processing jobs
processing_jobs = {}

# In-memory storage for embedding indices and graph databases
embedding_indices = {}
graph_databases = {}


def cleanup_old_temp_dirs():
    """
    Clean up old temporary repository directories
    """
    import shutil
    import time
    
    temp_dir = "./temp_repos"
    if not os.path.exists(temp_dir):
        return
    
    try:
        current_time = time.time()
        # Remove directories older than 1 hour
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                try:
                    item_age = current_time - os.path.getctime(item_path)
                    if item_age > 3600:  # 1 hour
                        print(f"Cleaning up old temp directory: {item}")
                        shutil.rmtree(item_path, ignore_errors=True)
                except Exception as e:
                    print(f"Failed to cleanup {item}: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")


# Cleanup old temp directories on startup
cleanup_old_temp_dirs()

class GitHubRepoRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = "main"

class ChatRequest(BaseModel):
    repo_id: str
    question: str
    conversation_history: Optional[List[Dict]] = []

class GraphData(BaseModel):
    nodes: List[Dict]
    edges: List[Dict]
    repo_name: str

@app.get("/")
async def root():
    return {"message": "CodeExplorer AI API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/clone-repo")
async def clone_repo(request: GitHubRepoRequest, background_tasks: BackgroundTasks):
    """
    Clone a GitHub repository and start graph building process
    """
    job_id = str(uuid.uuid4())
    
    # Start background processing
    background_tasks.add_task(process_repository, job_id, request.repo_url, request.branch)
    
    processing_jobs[job_id] = {
        "status": "processing",
        "repo_url": request.repo_url,
        "progress": 0,
        "message": "Cloning repository..."
    }
    
    return {"job_id": job_id, "status": "processing"}

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a processing job
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return processing_jobs[job_id]

@app.get("/api/graph/{job_id}")
async def get_graph(job_id: str):
    """
    Get the generated graph data for a job with Sugiyama layout
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Graph not ready yet")
    
    nodes = job.get("nodes", [])
    edges = job.get("edges", [])
    
    # Apply Sugiyama layout to full graph
    layout = create_graph_layout(nodes, edges)
    positions = layout.sugiyama_layout(nodes, edges)
    
    # Add positions to nodes
    for node in nodes:
        if node['id'] in positions:
            node['position'] = {
                'x': positions[node['id']][0],
                'y': positions[node['id']][1]
            }
    
    return {
        "nodes": nodes,
        "edges": edges,
        "repo_name": job.get("repo_name", "")
    }


@app.get("/api/node/{job_id}/{node_id}")
async def get_node_details(job_id: str, node_id: str):
    """
    Get details for a specific node and its subgraph
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Graph not ready yet")
    
    # Get the node
    nodes = job.get("nodes", [])
    edges = job.get("edges", [])
    
    print(f"Looking for node with ID: {node_id}")
    print(f"Available nodes: {[n['id'] for n in nodes[:10]]}")  # Log first 10 node IDs
    
    node = next((n for n in nodes if n["id"] == node_id), None)
    if not node:
        print(f"Node {node_id} not found in graph")
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    print(f"Found node: {node}")
    
    # Get connected nodes and edges
    connected_node_ids = set()
    connected_edges = []
    
    # Find edges connected to this node
    for edge in edges:
        if edge["source"] == node_id or edge["target"] == node_id:
            connected_edges.append(edge)
            connected_node_ids.add(edge["source"])
            connected_node_ids.add(edge["target"])
    
    # Get connected nodes
    connected_nodes = [n for n in nodes if n["id"] in connected_node_ids]
    
    # Get file content if it's a file node
    file_content = None
    if node.get("type") == "file" and node.get("data", {}).get("path"):
        repo_path = job.get("repo_path")
        if repo_path:
            file_path = os.path.join(repo_path, node["data"]["path"])
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
    
    return {
        "node": node,
        "connected_nodes": connected_nodes,
        "connected_edges": connected_edges,
        "file_content": file_content
    }


@app.post("/api/explain-node")
async def explain_node(request: dict):
    """
    Use LLM to explain a node's functionality
    """
    job_id = request.get("job_id")
    node = request.get("node")
    file_content = request.get("file_content")
    
    if not job_id or not node:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get embedding index and graph database
    if job_id not in embedding_indices or job_id not in graph_databases:
        raise HTTPException(status_code=500, detail="Graph data not available")
    
    # Create LLM client
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    api_base_url = os.getenv("OPENAI_API_BASE_URL")
    
    llm_client = create_llm_client(api_key=api_key, model=model, api_base_url=api_base_url)
    
    # Build explanation prompt
    node_type = node.get("type", "unknown")
    node_name = node.get("label") or node.get("data", {}).get("name", "unknown")
    
    prompt = f"Explain the functionality of this {node_type} named '{node_name}' in the codebase."
    
    if file_content:
        prompt += f"\n\nHere is the file content:\n```\n{file_content[:5000]}\n```"
    
    prompt += "\n\nProvide a clear, concise explanation of what this code does, its purpose, and how it fits into the overall codebase."
    
    # Generate explanation
    explanation = llm_client.generate_response(prompt, [], [])
    
    return {
        "explanation": explanation
    }


@app.get("/api/repo-overview/{job_id}")
async def get_repo_overview(job_id: str):
    """
    Get repository overview statistics and summary
    """
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Graph not ready yet")
        
        nodes = job.get("nodes", [])
        repo_path = job.get("repo_path")
        
        # Calculate statistics
        stats = {
            "total_files": 0,
            "total_classes": 0,
            "total_functions": 0,
            "languages": {},
            "lines_of_code": 0,
            "complexity_score": 0
        }
        
        # Count nodes by type
        for node in nodes:
            node_type = node.get("type")
            if node_type == "file":
                stats["total_files"] += 1
                # Count lines of code
                file_path = node.get("data", {}).get("full_path")
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = len(f.readlines())
                            stats["lines_of_code"] += lines
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
            elif node_type == "class":
                stats["total_classes"] += 1
            elif node_type == "function":
                stats["total_functions"] += 1
        
        # Calculate languages (simplified - currently only Python)
        stats["languages"] = {"Python": stats["total_files"]}
        
        # Calculate complexity score (simplified based on functions/classes ratio)
        if stats["total_files"] > 0:
            stats["complexity_score"] = round((stats["total_classes"] + stats["total_functions"]) / stats["total_files"], 2)
        
        # Get last updated time
        last_updated = "Unknown"
        if repo_path and os.path.exists(repo_path):
            try:
                import datetime
                timestamp = os.path.getmtime(repo_path)
                last_updated = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Error getting timestamp: {e}")
        
        return {
            "stats": stats,
            "repo_name": job.get("repo_name", ""),
            "last_updated": last_updated
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_repo_overview: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/project-structure/{job_id}")
async def get_project_structure(job_id: str):
    """
    Get project structure as a tree
    """
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Graph not ready yet")
        
        nodes = job.get("nodes", [])
        
        # Build tree structure from file nodes
        tree = {}
        
        for node in nodes:
            if node.get("type") == "file":
                path = node.get("data", {}).get("path", "")
                if path:
                    # Split path into components
                    parts = path.split("/")
                    current = tree
                    
                    for i, part in enumerate(parts):
                        if part not in current:
                            if i == len(parts) - 1:
                                # This is the file
                                current[part] = {
                                    "type": "file",
                                    "name": part,
                                    "path": path,
                                    "node_id": node["id"],
                                    "children": {}
                                }
                            else:
                                # This is a directory
                                current[part] = {
                                    "type": "directory",
                                    "name": part,
                                    "children": {}
                                }
                        current = current[part]["children"]
        
        return {
            "tree": tree,
            "repo_name": job.get("repo_name", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_project_structure: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/repo-summary/{job_id}")
async def get_repo_summary(job_id: str):
    """
    Generate a comprehensive summary of the repository using LLM
    """
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Graph not ready yet")
        
        nodes = job.get("nodes", [])
        edges = job.get("edges", [])
        repo_name = job.get("repo_name", "")
        
        # Analyze repository structure
        file_nodes = [n for n in nodes if n.get("type") == "file"]
        class_nodes = [n for n in nodes if n.get("type") == "class"]
        function_nodes = [n for n in nodes if n.get("type") == "function"]
        
        # Get sample file paths and names
        sample_files = [n.get("data", {}).get("path", "") for n in file_nodes[:10]]
        sample_classes = [n.get("label", n.get("data", {}).get("name", "")) for n in class_nodes[:5]]
        sample_functions = [n.get("label", n.get("data", {}).get("name", "")) for n in function_nodes[:5]]
        
        # Create LLM client
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        api_base_url = os.getenv("OPENAI_API_BASE_URL")
        
        llm_client = create_llm_client(api_key=api_key, model=model, api_base_url=api_base_url)
        
        # Build summary prompt
        summary_prompt = f"""Analyze this repository named '{repo_name}' and provide a comprehensive summary for a beginner.

Repository Overview:
- Total files: {len(file_nodes)}
- Total classes: {len(class_nodes)}
- Total functions: {len(function_nodes)}

Sample files:
{chr(10).join([f"- {f}" for f in sample_files])}

Sample classes:
{chr(10).join([f"- {c}" for c in sample_classes])}

Sample functions:
{chr(10).join([f"- {fn}" for fn in sample_functions])}

Please provide a summary that answers these questions:
1. What does this repository do? (Purpose/Mission)
2. What are the main features and functionalities?
3. How does it work? (Architecture/Flow)

Keep the summary concise but informative (2-3 paragraphs total). Write in a way that's easy for a beginner to understand."""
        
        # Generate summary
        summary_response = llm_client.generate_response(summary_prompt, [], [])
        
        return {
            "summary": summary_response,
            "repo_name": repo_name
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_repo_summary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/generate-learning-path/{job_id}")
async def generate_learning_path(job_id: str):
    """
    Generate a personalized learning path for understanding the repository using LLM
    """
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Graph not ready yet")
        
        nodes = job.get("nodes", [])
        edges = job.get("edges", [])
        repo_name = job.get("repo_name", "")
        
        # Analyze repository structure
        file_nodes = [n for n in nodes if n.get("type") == "file"]
        class_nodes = [n for n in nodes if n.get("type") == "class"]
        function_nodes = [n for n in nodes if n.get("type") == "function"]
        
        # Identify potential entry points
        entry_points = []
        for node in file_nodes:
            path = node.get("data", {}).get("path", "")
            if any(keyword in path.lower() for keyword in ["main", "app", "index", "__init__", "run", "start"]):
                entry_points.append({
                    "name": node.get("label", path),
                    "path": path,
                    "node_id": node["id"]
                })
        
        # Identify important modules (files with many classes/functions)
        file_complexity = {}
        for node in file_nodes:
            file_path = node.get("data", {}).get("path", "")
            file_complexity[file_path] = 0
        
        for edge in edges:
            if edge.get("source") in file_complexity:
                file_complexity[edge.get("source")] += 1
            if edge.get("target") in file_complexity:
                file_complexity[edge.get("target")] += 1
        
        # Get top 5 most complex files
        important_modules = sorted(file_complexity.items(), key=lambda x: x[1], reverse=True)[:5]
        important_modules = [
            {
                "name": path.split("/")[-1],
                "path": path,
                "complexity": complexity,
                "node_id": next((n["id"] for n in file_nodes if n.get("data", {}).get("path") == path), None)
            }
            for path, complexity in important_modules
        ]
        
        # Create LLM client
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        api_base_url = os.getenv("OPENAI_API_BASE_URL")
        
        llm_client = create_llm_client(api_key=api_key, model=model, api_base_url=api_base_url)
        
        # Build analysis prompt
        analysis_prompt = f"""Analyze this repository named '{repo_name}' and create a step-by-step learning path for a beginner to understand the project.

Repository Overview:
- Total files: {len(file_nodes)}
- Total classes: {len(class_nodes)}
- Total functions: {len(function_nodes)}

Potential Entry Points:
{chr(10).join([f"- {ep['name']} ({ep['path']})" for ep in entry_points[:3]])}

Important Modules:
{chr(10).join([f"- {im['name']} ({im['path']}) - complexity: {im['complexity']}" for im in important_modules[:3]])}

Sample file paths:
{chr(10).join([n.get("data", {}).get("path", "") for n in file_nodes[:5]])}

Create a learning path with 5-7 steps. Each step should include:
1. A clear title
2. What to look at (specific files/modules)
3. Why it's important
4. What the beginner will learn

Format as JSON array with structure:
[
  {{
    "title": "Step title",
    "content": "Detailed explanation",
    "highlight": "file_path_or_module_name",
    "files_to_examine": ["file1.py", "file2.py"]
  }}
]

Focus on helping a beginner understand the project structure and main functionality step by step."""
        
        # Generate learning path
        learning_path_response = llm_client.generate_response(analysis_prompt, [], [])
        
        # Try to parse JSON response
        try:
            import json
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in learning_path_response:
                json_start = learning_path_response.find("```json") + 7
                json_end = learning_path_response.find("```", json_start)
                learning_path_json = learning_path_response[json_start:json_end].strip()
            elif "```" in learning_path_response:
                json_start = learning_path_response.find("```") + 3
                json_end = learning_path_response.find("```", json_start)
                learning_path_json = learning_path_response[json_start:json_end].strip()
            else:
                learning_path_json = learning_path_response.strip()
            
            learning_steps = json.loads(learning_path_json)
        except json.JSONDecodeError:
            # Fallback to manual steps if JSON parsing fails
            learning_steps = [
                {
                    "title": "Start with Entry Points",
                    "content": f"Begin by examining the main entry points of the application. Look at files like {entry_points[0]['name'] if entry_points else 'main.py'} to understand how the application starts.",
                    "highlight": entry_points[0]["path"] if entry_points else None,
                    "files_to_examine": [ep["path"] for ep in entry_points[:2]]
                },
                {
                    "title": "Understand Core Modules",
                    "content": f"Explore the core modules that handle the main functionality. Start with {important_modules[0]['name'] if important_modules else 'core modules'} to understand the business logic.",
                    "highlight": important_modules[0]["path"] if important_modules else None,
                    "files_to_examine": [im["path"] for im in important_modules[:2]]
                },
                {
                    "title": "Review Data Structures",
                    "content": "Look at how data is structured and flows through the application. Examine classes and their relationships.",
                    "highlight": None,
                    "files_to_examine": [n.get("data", {}).get("path") for n in class_nodes[:3]]
                },
                {
                    "title": "Explore Key Functions",
                    "content": "Study the main functions that drive the application's behavior. Focus on functions with high connectivity.",
                    "highlight": None,
                    "files_to_examine": [n.get("data", {}).get("path") for n in function_nodes[:3]]
                },
                {
                    "title": "Understand Dependencies",
                    "content": "Review how different modules depend on each other. This will help you understand the overall architecture.",
                    "highlight": None,
                    "files_to_examine": []
                }
            ]
        
        return {
            "learning_path": learning_steps,
            "repo_name": repo_name,
            "entry_points": entry_points,
            "important_modules": important_modules
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in generate_learning_path: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/search-files/{job_id}")
async def search_files(job_id: str, request: dict):
    """
    Search for files, classes, and functions in the repository
    """
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Graph not ready yet")
        
        nodes = job.get("nodes", [])
        query = request.get("query", "").lower()
        node_type_filter = request.get("node_type")  # "file", "class", "function", or None for all
        
        if not query:
            return {
                "results": [],
                "total": 0
            }
        
        # Search nodes
        results = []
        for node in nodes:
            # Filter by node type if specified
            if node_type_filter and node.get("type") != node_type_filter:
                continue
            
            # Search in label, name, and path
            label = node.get("label", "").lower()
            name = node.get("data", {}).get("name", "").lower()
            path = node.get("data", {}).get("path", "").lower()
            
            if (query in label or query in name or query in path):
                results.append({
                    "id": node["id"],
                    "type": node.get("type"),
                    "label": node.get("label"),
                    "name": node.get("data", {}).get("name"),
                    "path": node.get("data", {}).get("path"),
                    "full_path": node.get("data", {}).get("full_path")
                })
        
        return {
            "results": results,
            "total": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in search_files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat with the repository using graph retriever + LLM
    """
    if request.repo_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    job = processing_jobs[request.repo_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Repository not ready")
    
    # Get embedding index and graph database
    if request.repo_id not in embedding_indices or request.repo_id not in graph_databases:
        raise HTTPException(status_code=500, detail="Graph data not available")
    
    embedding_index = embedding_indices[request.repo_id]
    graph_db = graph_databases[request.repo_id]
    
    # Create retriever
    retriever = create_graph_retriever(embedding_index, graph_db)
    
    # Retrieve relevant context
    context = retriever.retrieve(request.question, k=10)
    
    # Create LLM client with API key and base URL from environment
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    api_base_url = os.getenv("OPENAI_API_BASE_URL")
    
    llm_client = create_llm_client(api_key=api_key, model=model, api_base_url=api_base_url)
    
    # Generate response
    answer = llm_client.generate_response(
        request.question,
        context,
        request.conversation_history
    )
    
    # Extract sources
    sources = []
    for node in context[:5]:
        if node.get("type") == "file":
            sources.append(node.get("data", {}).get("path", node.get("label", "")))
        elif node.get("type") == "class":
            name = node.get("data", {}).get("name", node.get("label", ""))
            file_path = node.get("data", {}).get("file", "")
            sources.append(f"{name} in {file_path}")
    
    response = {
        "answer": answer,
        "sources": sources
    }
    
    return response

async def process_repository(job_id: str, repo_url: str, branch: str):
    """
    Background task to process a repository:
    1. Clone the repository
    2. Build code graph using CodeFuse-CGM
    3. Generate embeddings
    4. Store in graph database
    """
    import traceback
    
    try:
        # Update status
        processing_jobs[job_id]["progress"] = 10
        processing_jobs[job_id]["message"] = "Cloning repository..."
        
        # Clone repository
        try:
            repo_path = clone_github_repo(repo_url)
            print(f"Successfully cloned repository to: {repo_path}")
        except Exception as e:
            print(f"Git clone error: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Failed to clone repository: {str(e)}")
        
        processing_jobs[job_id]["progress"] = 30
        processing_jobs[job_id]["message"] = "Building code graph..."
        
        # Build code graph
        try:
            graph_data = await build_code_graph(repo_path)
            print(f"Successfully built graph with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")
        except Exception as e:
            print(f"Graph building error: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Failed to build code graph: {str(e)}")
        
        processing_jobs[job_id]["progress"] = 70
        processing_jobs[job_id]["message"] = "Generating embeddings..."
        
        # Generate embeddings
        try:
            await generate_embeddings(graph_data, job_id)
            print("Successfully generated embeddings")
        except Exception as e:
            print(f"Embedding generation error: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Failed to generate embeddings: {str(e)}")
        
        processing_jobs[job_id]["progress"] = 90
        processing_jobs[job_id]["message"] = "Finalizing..."
        
        # Store results
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["message"] = "Completed"
        processing_jobs[job_id]["nodes"] = graph_data["nodes"]
        processing_jobs[job_id]["edges"] = graph_data["edges"]
        processing_jobs[job_id]["repo_name"] = graph_data["repo_name"]
        processing_jobs[job_id]["repo_path"] = repo_path
        
        print(f"Job {job_id} completed successfully")
        
    except Exception as e:
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Error: {str(e)}"
        print(f"Error processing repository: {e}")
        traceback.print_exc()

def clone_github_repo(repo_url: str) -> str:
    """
    Clone a GitHub repository (synchronous function)
    """
    import git
    import shutil
    import time
    import uuid
    
    # Extract repo name from URL
    try:
        repo_name = repo_url.split("/")[-1].replace(".git", "")
    except Exception as e:
        raise Exception(f"Invalid repository URL: {repo_url}")
    
    # Add unique suffix to avoid conflicts
    unique_suffix = str(uuid.uuid4())[:8]
    repo_path = f"./temp_repos/{repo_name}_{unique_suffix}"
    
    # Create temp directory if it doesn't exist
    try:
        os.makedirs("./temp_repos", exist_ok=True)
    except Exception as e:
        raise Exception(f"Failed to create temp directory: {str(e)}")
    
    # Clone the repository
    try:
        print(f"Cloning {repo_url} to {repo_path}")
        
        # Use git clone with depth 1 for faster cloning (no specific branch, use default)
        git.Repo.clone_from(
            repo_url, 
            repo_path, 
            depth=1  # Shallow clone for speed
        )
        
        print(f"Successfully cloned repository")
        
        if not os.path.exists(repo_path):
            raise Exception("Repository directory was not created")
            
    except git.exc.GitCommandError as e:
        # Clean up partial clone
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path, ignore_errors=True)
            except:
                pass
        raise Exception(f"Git clone failed: {str(e)}")
    except Exception as e:
        # Clean up partial clone
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path, ignore_errors=True)
            except:
                pass
        raise Exception(f"Failed to clone repository: {str(e)}")
    
    return repo_path

async def build_code_graph(repo_path: str) -> Dict:
    """
    Build code graph using CodeFuse-CGM components
    """
    # Use the graph builder to generate the actual graph
    graph_data = build_graph_for_repo(repo_path)
    return graph_data

async def generate_embeddings(graph_data: Dict, job_id: str):
    """
    Generate embeddings for graph nodes and create graph database
    """
    # Create embedding index
    embedding_index = create_embedding_index(graph_data)
    embedding_indices[job_id] = embedding_index
    
    # Create graph database
    graph_db = create_graph_database(graph_data)
    graph_databases[job_id] = graph_db
    
    # Save to disk (optional)
    # embedding_index.save(f"./temp_indices/{job_id}.pkl")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
