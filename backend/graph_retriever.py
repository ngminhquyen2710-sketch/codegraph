"""
Graph Retriever Module - Retrieves relevant code context from the graph database
"""
import numpy as np
from typing import Dict, List, Tuple
from rapidfuzz import process, fuzz


class GraphRetriever:
    """
    Retrieves relevant code context from the graph database using:
    1. Keyword matching (extractor)
    2. Semantic search (inferer with embeddings)
    """
    
    def __init__(self, embedding_index, graph_database):
        self.embedding_index = embedding_index
        self.graph_db = graph_database
    
    def retrieve(self, query: str, k: int = 10) -> List[Dict]:
        """
        Retrieve relevant nodes for a query
        Combines keyword matching and semantic search
        """
        # Method 1: Keyword matching (extractor)
        keyword_results = self._keyword_search(query)
        
        # Method 2: Semantic search (inferer)
        semantic_results = self._semantic_search(query, k)
        
        # Combine and deduplicate results
        combined_results = self._combine_results(keyword_results, semantic_results, k)
        
        # Expand to include neighbors (subgraph expansion)
        expanded_results = self._expand_subgraph(combined_results, depth=1)
        
        return expanded_results
    
    def _keyword_search(self, query: str) -> List[Dict]:
        """
        Search using keyword matching (similar to CodeFuse-CGM's extractor)
        """
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        results = []
        for keyword in keywords:
            # Search by name
            matches = self.graph_db.search_by_name(keyword)
            results.extend(matches)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for result in results:
            if result["id"] not in seen:
                seen.add(result["id"])
                unique_results.append(result)
        
        return unique_results
    
    def _semantic_search(self, query: str, k: int = 10) -> List[Dict]:
        """
        Search using semantic similarity with embeddings
        """
        # Generate query embedding (simple hash-based for demo)
        query_embedding = self._generate_query_embedding(query)
        
        # Search in embedding index
        search_results = self.embedding_index.search(query_embedding, k)
        
        # Retrieve node data
        results = []
        for node_id, distance in search_results:
            node = self.graph_db.get_node(node_id)
            if node:
                node["relevance_score"] = 1.0 / (1.0 + distance)  # Convert distance to score
                results.append(node)
        
        return results
    
    def _generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate embedding for query (placeholder)
        In production, this would use CodeFuse-CGE
        """
        # Simple hash-based embedding for demo
        hash_val = hash(query)
        np.random.seed(hash_val % (2**32))
        embedding = np.random.randn(self.embedding_index.embedding_dim).astype('float32')
        return embedding
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query
        """
        # Simple keyword extraction
        # Split by common delimiters and filter
        import re
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'again', 'further', 'then', 'once'}
        
        # Extract words
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _combine_results(self, keyword_results: List[Dict], 
                        semantic_results: List[Dict], k: int) -> List[Dict]:
        """
        Combine results from keyword and semantic search
        """
        # Score combination
        scored_results = {}
        
        # Keyword results get base score
        for result in keyword_results:
            node_id = result["id"]
            scored_results[node_id] = {
                "node": result,
                "score": 0.5  # Base score for keyword match
            }
        
        # Semantic results get their relevance score
        for result in semantic_results:
            node_id = result["id"]
            if node_id in scored_results:
                # Boost if both methods found it
                scored_results[node_id]["score"] += result.get("relevance_score", 0.5)
            else:
                scored_results[node_id] = {
                    "node": result,
                    "score": result.get("relevance_score", 0.5)
                }
        
        # Sort by score and return top k
        sorted_results = sorted(scored_results.values(), 
                               key=lambda x: x["score"], 
                               reverse=True)[:k]
        
        return [item["node"] for item in sorted_results]
    
    def _expand_subgraph(self, nodes: List[Dict], depth: int = 1) -> List[Dict]:
        """
        Expand the subgraph to include neighboring nodes
        """
        node_ids = [node["id"] for node in nodes]
        subgraph = self.graph_db.get_subgraph(node_ids, depth)
        
        return subgraph["nodes"]


class LLMClient:
    """
    LLM client for generating responses
    Supports OpenAI API and custom endpoints (like OpenRouter)
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo", api_base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.api_base_url = api_base_url
        
        # For demo, we'll use a simple rule-based response
        # In production, this would call OpenAI API or similar
        self.use_mock = api_key is None
    
    def generate_response(self, question: str, context: List[Dict], 
                         conversation_history: List[Dict] = None) -> str:
        """
        Generate a response to the question using the retrieved context
        """
        if self.use_mock:
            return self._generate_mock_response(question, context)
        else:
            return self._generate_openai_response(question, context, conversation_history)
    
    def _generate_mock_response(self, question: str, context: List[Dict]) -> str:
        """
        Generate a mock response for demonstration
        """
        # Extract relevant information from context
        files = [node for node in context if node.get("type") == "file"]
        classes = [node for node in context if node.get("type") == "class"]
        functions = [node for node in context if node.get("type") == "function"]
        
        response_parts = []
        
        if files:
            response_parts.append(f"I found {len(files)} relevant file(s):")
            for file in files[:3]:
                file_path = file.get("data", {}).get("path", file.get("label", ""))
                response_parts.append(f"- {file_path}")
        
        if classes:
            response_parts.append(f"\nI found {len(classes)} relevant class(es):")
            for cls in classes[:3]:
                class_name = cls.get("label", cls.get("data", {}).get("name", ""))
                response_parts.append(f"- {class_name}")
        
        if functions:
            response_parts.append(f"\nI found {len(functions)} relevant function(s):")
            for func in functions[:3]:
                func_name = func.get("label", func.get("data", {}).get("name", ""))
                response_parts.append(f"- {func_name}")
        
        if not response_parts:
            response_parts.append("I searched the code graph but couldn't find specific matches for your query. Try rephrasing your question with different keywords.")
        
        response_parts.append("\n\nThis is a demonstration response. The full implementation would use an LLM (like GPT-4) to provide more detailed and contextual answers based on the retrieved code context.")
        
        return "\n".join(response_parts)
    
    def _generate_openai_response(self, question: str, context: List[Dict],
                                  conversation_history: List[Dict] = None) -> str:
        """
        Generate response using OpenAI API or custom endpoint
        """
        try:
            import openai
            
            # Create client with custom base URL if provided
            if self.api_base_url:
                client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base_url
                )
            else:
                client = openai.OpenAI(api_key=self.api_key)
            
            # Build context string
            context_str = self._format_context(context)
            
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions about code repositories. Use the provided code context to give accurate and detailed answers."
                }
            ]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current question with context
            messages.append({
                "role": "user",
                "content": f"Question: {question}\n\nRelevant Code Context:\n{context_str}"
            })
            
            # Generate response
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _format_context(self, context: List[Dict]) -> str:
        """
        Format the retrieved context for the LLM
        """
        context_parts = []
        
        for node in context:
            node_type = node.get("type", "unknown")
            label = node.get("label", "")
            data = node.get("data", {})
            
            if node_type == "file":
                path = data.get("path", label)
                context_parts.append(f"File: {path}")
            elif node_type == "class":
                name = data.get("name", label)
                file_path = data.get("file", "")
                context_parts.append(f"Class: {name} (in {file_path})")
            elif node_type == "function":
                name = data.get("name", label)
                class_name = data.get("class", "")
                file_path = data.get("file", "")
                if class_name:
                    context_parts.append(f"Method: {name} (in class {class_name}, file {file_path})")
                else:
                    context_parts.append(f"Function: {name} (in {file_path})")
        
        return "\n".join(context_parts)


def create_graph_retriever(embedding_index, graph_database) -> GraphRetriever:
    """
    Convenience function to create a graph retriever
    """
    return GraphRetriever(embedding_index, graph_database)


def create_llm_client(api_key: str = None, model: str = "gpt-3.5-turbo", api_base_url: str = None) -> LLMClient:
    """
    Convenience function to create an LLM client
    """
    return LLMClient(api_key, model, api_base_url)
