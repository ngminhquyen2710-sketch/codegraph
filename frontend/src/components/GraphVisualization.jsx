import { useState, useEffect, useCallback } from 'react'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  useReactFlow,
  ReactFlowProvider
} from 'reactflow'
import 'reactflow/dist/style.css'
import axios from 'axios'
import { ArrowLeft, File, Code2, Database, Folder, Sparkles, Loader2, Send, Bot, User, GripVertical, RotateCw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'

const GraphVisualization = ({ repoId, onLoaded, repoName, highlightNodePath }) => {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  const reactFlowInstance = useReactFlow()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)
  const [originalNodes, setOriginalNodes] = useState([])
  const [originalEdges, setOriginalEdges] = useState([])
  const [fileContent, setFileContent] = useState('')
  const [explanation, setExplanation] = useState('')
  const [isExplaining, setIsExplaining] = useState(false)
  
  // Branch highlighting and movement
  const [draggedNodeId, setDraggedNodeId] = useState(null)
  const [branchNodeIds, setBranchNodeIds] = useState(new Set())
  const [branchEdgeIds, setBranchEdgeIds] = useState(new Set())
  const [initialPositions, setInitialPositions] = useState(new Map())
  
  // Panel positions and sizes
  const [filePanelPos, setFilePanelPos] = useState({ x: 20, y: 80 })
  const [filePanelSize, setFilePanelSize] = useState({ width: 400, height: 300 })
  const [aiPanelPos, setAiPanelPos] = useState({ x: 440, y: 80 })
  const [aiPanelSize, setAiPanelSize] = useState({ width: 400, height: 400 })
  
  // Chat messages for AI panel
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)

  // Highlight node from external source (e.g., tour)
  useEffect(() => {
    if (highlightNodePath && nodes.length > 0) {
      console.log('Looking for node with path:', highlightNodePath)
      
      // Try multiple path formats
      const nodeToHighlight = nodes.find(node => {
        const nodePath = node.data?.path || ''
        const nodeLabel = node.label || ''
        
        // Exact match
        if (nodePath === highlightNodePath || nodeLabel === highlightNodePath) {
          return true
        }
        
        // Try with different separators
        const normalizedHighlight = highlightNodePath.replace(/\\/g, '/').replace(/\//g, '/')
        const normalizedNodePath = nodePath.replace(/\\/g, '/').replace(/\//g, '/')
        
        if (normalizedNodePath === normalizedHighlight) {
          return true
        }
        
        // Try partial match (filename only)
        const highlightFileName = highlightNodePath.split('/').pop().split('\\').pop()
        const nodeFileName = nodePath.split('/').pop().split('\\').pop()
        
        if (highlightFileName === nodeFileName && highlightFileName.length > 5) {
          return true
        }
        
        return false
      })
      
      console.log('Found node:', nodeToHighlight)
      
      if (nodeToHighlight) {
        // Select the node
        setSelectedNode(nodeToHighlight)
        
        // Center the view on the node
        if (reactFlowInstance) {
          reactFlowInstance.setCenter(nodeToHighlight.position.x, nodeToHighlight.position.y, { zoom: 1.5, duration: 800 })
        }
        
        // Load file content using the same logic as handleNodeClick
        (async () => {
          try {
            console.log('Fetching node details for:', nodeToHighlight.id)
            const response = await axios.get(`http://localhost:8000/api/node/${repoId}/${nodeToHighlight.id}`)
            const data = response.data
            console.log('Node details:', data)
            
            setSelectedNode(data.node)
            setFileContent(data.file_content || '')
            setExplanation('')
            setChatMessages([])
          } catch (err) {
            console.error('Error loading node details:', err)
          }
        })()
      } else {
        console.warn('Node not found for path:', highlightNodePath)
        console.log('Available nodes:', nodes.map(n => ({ id: n.id, path: n.data?.path, label: n.label })))
      }
    }
  }, [highlightNodePath, nodes])

  // Poll job status
  const pollJobStatus = useCallback(async () => {
    try {
      console.log('Checking job status for:', repoId)
      const response = await axios.get(`http://localhost:8000/api/job-status/${repoId}`)
      const job = response.data
      console.log('Job status:', job)

      if (job.status === 'completed') {
        console.log('Job completed, loading graph data...')
        // Load graph data
        await loadGraphData()
      } else if (job.status === 'failed') {
        const errorMsg = job.message || 'Failed to process repository'
        console.error('Job failed:', errorMsg)
        setError(errorMsg)
        setIsLoading(false)
      } else {
        console.log('Job still processing, polling again in 2s...')
        // Continue polling
        setTimeout(pollJobStatus, 2000)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to check job status'
      console.error('Status check error:', errorMsg)
      setError(errorMsg)
      setIsLoading(false)
    }
  }, [repoId])

  // Load graph data
  const loadGraphData = useCallback(async () => {
    try {
      console.log('Loading graph data for:', repoId)
      const response = await axios.get(`http://localhost:8000/api/graph/${repoId}`)
      const graphData = response.data
      console.log('Graph data received:', graphData)
      console.log('Number of nodes:', graphData.nodes.length)
      console.log('Number of edges:', graphData.edges.length)

      // Transform nodes for React Flow
      const flowNodes = graphData.nodes.map((node, index) => ({
        id: node.id,
        type: getNodeStyle(node.type),
        position: node.position || { x: Math.random() * 400 + 50, y: Math.random() * 400 + 50 },
        data: { label: node.label || node.data?.name || node.id, ...node.data }
      }))

      console.log('Transformed flow nodes:', flowNodes)

      // Transform edges for React Flow
      const flowEdges = graphData.edges.map((edge) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        label: edge.type,
        style: { stroke: getEdgeColor(edge.type) }
      }))

      console.log('Transformed flow edges:', flowEdges)

      setNodes(flowNodes)
      setEdges(flowEdges)
      setOriginalNodes(flowNodes)
      setOriginalEdges(flowEdges)
      setIsLoading(false)
      onLoaded(graphData.repo_name)
      console.log('Graph loaded successfully')
    } catch (err) {
      console.error('Error loading graph data:', err)
      setError('Failed to load graph data')
      setIsLoading(false)
    }
  }, [repoId, setNodes, setEdges, onLoaded])

  // Apply branch highlighting
  useEffect(() => {
    if (draggedNodeId) {
      setNodes(currentNodes => currentNodes.map(n => {
        if (branchNodeIds.has(n.id)) {
          return {
            ...n,
            style: {
              ...n.style,
              border: '3px solid #f59e0b',
              boxShadow: '0 0 10px rgba(245, 158, 11, 0.5)'
            }
          }
        }
        return {
          ...n,
          style: {
            ...n.style,
            opacity: 0.3
          }
        }
      }))
      
      setEdges(currentEdges => currentEdges.map(e => {
        if (branchEdgeIds.has(e.id)) {
          return {
            ...e,
            style: {
              ...e.style,
              stroke: '#f59e0b',
              strokeWidth: 3,
              opacity: 1
            }
          }
        }
        return {
          ...e,
          style: {
            ...e.style,
            opacity: 0.2
          }
        }
      }))
    } else {
      // Reset highlighting
      setNodes(currentNodes => currentNodes.map(n => ({
        ...n,
        style: {}
      })))
      setEdges(currentEdges => currentEdges.map(e => ({
        ...e,
        style: {
          stroke: getEdgeColor(e.label),
          opacity: 1
        }
      })))
    }
  }, [draggedNodeId, branchNodeIds, branchEdgeIds, setNodes, setEdges])

  const handleNodeClick = useCallback(async (event, node) => {
    try {
      console.log('Node clicked:', node)
      console.log('Fetching node details for:', node.id)
      const response = await axios.get(`http://localhost:8000/api/node/${repoId}/${node.id}`)
      const data = response.data
      console.log('Node details:', data)
      
      setSelectedNode(data.node)
      setFileContent(data.file_content || '')
      setExplanation('')  // Reset explanation
      setChatMessages([])  // Reset chat
      
      // Transform connected nodes for React Flow
      const connectedFlowNodes = data.connected_nodes.map((n, index) => ({
        id: n.id,
        type: getNodeStyle(n.type),
        position: {
          x: n.id === data.node.id ? 400 : Math.random() * 600 + 100,
          y: n.id === data.node.id ? 300 : Math.random() * 400 + 100
        },
        data: { label: n.label || n.data?.name || n.id, ...n.data },
        style: n.id === data.node.id ? { border: '3px solid #f59e0b', borderWidth: '3px' } : {}
      }))
      
      // Transform connected edges for React Flow
      const connectedFlowEdges = data.connected_edges.map((edge) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        label: edge.type,
        style: { stroke: getEdgeColor(edge.type) }
      }))
      
      setNodes(connectedFlowNodes)
      setEdges(connectedFlowEdges)
    } catch (err) {
      console.error('Error loading node details:', err)
      console.error('Error response:', err.response?.data)
      alert('Failed to load node details. This node might not exist in the graph.')
    }
  }, [repoId, setNodes, setEdges])

  const handleBackToFullGraph = useCallback(() => {
    setSelectedNode(null)
    setFileContent('')
    setExplanation('')
    setChatMessages([])
    setNodes(originalNodes)
    setEdges(originalEdges)
  }, [originalNodes, originalEdges, setNodes, setEdges])

  // Find all nodes in a branch (downstream from a node)
  const findBranchNodes = useCallback((nodeId, currentEdges) => {
    const branchNodes = new Set([nodeId])
    const branchEdges = new Set()
    const queue = [nodeId]
    
    while (queue.length > 0) {
      const currentId = queue.shift()
      
      // Find all downstream edges and nodes
      currentEdges.forEach(edge => {
        if (edge.source === currentId) {
          branchEdges.add(edge.id)
          if (!branchNodes.has(edge.target)) {
            branchNodes.add(edge.target)
            queue.push(edge.target)
          }
        }
      })
    }
    
    return { branchNodes, branchEdges }
  }, [])

  // Handle node drag start
  const handleNodeDragStart = useCallback((event, node) => {
    console.log('Node drag started:', node.id)
    setDraggedNodeId(node.id)
    
    // Find branch nodes and edges
    const { branchNodes, branchEdges } = findBranchNodes(node.id, edges)
    setBranchNodeIds(branchNodes)
    setBranchEdgeIds(branchEdges)
    
    // Store initial positions
    const positions = new Map()
    nodes.forEach(n => {
      if (branchNodes.has(n.id)) {
        positions.set(n.id, { ...n.position })
      }
    })
    setInitialPositions(positions)
  }, [edges, nodes, findBranchNodes])

  // Handle node drag
  const handleNodeDrag = useCallback((event, node) => {
    if (!draggedNodeId) return
    
    const deltaX = node.position.x - initialPositions.get(node.id).x
    const deltaY = node.position.y - initialPositions.get(node.id).y
    
    // Move all branch nodes
    setNodes(currentNodes => currentNodes.map(n => {
      if (branchNodeIds.has(n.id)) {
        const initialPos = initialPositions.get(n.id)
        return {
          ...n,
          position: {
            x: initialPos.x + deltaX,
            y: initialPos.y + deltaY
          }
        }
      }
      return n
    }))
  }, [draggedNodeId, branchNodeIds, initialPositions, setNodes])

  // Handle node drag end
  const handleNodeDragStop = useCallback(() => {
    console.log('Node drag stopped')
    setDraggedNodeId(null)
    setBranchNodeIds(new Set())
    setBranchEdgeIds(new Set())
    setInitialPositions(new Map())
  }, [])

  // Navigation controls
  const handleZoomIn = useCallback(() => {
    zoomIn({ duration: 300 })
  }, [zoomIn])

  const handleZoomOut = useCallback(() => {
    zoomOut({ duration: 300 })
  }, [zoomOut])

  const handleFitView = useCallback(() => {
    fitView({ duration: 300 })
  }, [fitView])

  const handleRotate = useCallback(() => {
    // ReactFlow doesn't have built-in rotation, but we can simulate by adjusting node positions
    // For now, let's just fit view as a placeholder
    fitView({ duration: 300 })
  }, [fitView])

  const handleExplainNode = useCallback(async () => {
    if (!selectedNode) return
    
    setIsExplaining(true)
    try {
      const response = await axios.post('http://localhost:8000/api/explain-node', {
        job_id: repoId,
        node: selectedNode,
        file_content: fileContent
      })
      setExplanation(response.data.explanation)
      // Add explanation as first message in chat
      setChatMessages([
        { role: 'assistant', content: response.data.explanation }
      ])
    } catch (err) {
      console.error('Error explaining node:', err)
      setExplanation('Failed to generate explanation. Please try again.')
      setChatMessages([
        { role: 'assistant', content: 'Failed to generate explanation. Please try again.' }
      ])
    } finally {
      setIsExplaining(false)
    }
  }, [selectedNode, repoId, fileContent])

  const handleChatSend = useCallback(async () => {
    if (!chatInput.trim() || isChatLoading) return
    
    const userMessage = { role: 'user', content: chatInput }
    setChatMessages(prev => [...prev, userMessage])
    setChatInput('')
    setIsChatLoading(true)
    
    try {
      const response = await axios.post('http://localhost:8000/api/chat', {
        repo_id: repoId,
        question: chatInput,
        conversation_history: chatMessages
      })
      
      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources
      }
      
      setChatMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your question. Please try again.'
      }
      setChatMessages(prev => [...prev, errorMessage])
    } finally {
      setIsChatLoading(false)
    }
  }, [chatInput, chatMessages, isChatLoading, repoId])

  // Drag handlers
  const handleFilePanelDrag = useCallback((e) => {
    const startX = e.clientX - filePanelPos.x
    const startY = e.clientY - filePanelPos.y
    
    const handleMouseMove = (moveEvent) => {
      setFilePanelPos({
        x: moveEvent.clientX - startX,
        y: moveEvent.clientY - startY
      })
    }
    
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [filePanelPos])

  const handleAiPanelDrag = useCallback((e) => {
    const startX = e.clientX - aiPanelPos.x
    const startY = e.clientY - aiPanelPos.y
    
    const handleMouseMove = (moveEvent) => {
      setAiPanelPos({
        x: moveEvent.clientX - startX,
        y: moveEvent.clientY - startY
      })
    }
    
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [aiPanelPos])

  // Resize handlers
  const handleFilePanelResize = useCallback((e, direction) => {
    e.preventDefault()
    const startX = e.clientX
    const startY = e.clientY
    const startWidth = filePanelSize.width
    const startHeight = filePanelSize.height
    
    const handleMouseMove = (moveEvent) => {
      const deltaX = moveEvent.clientX - startX
      const deltaY = moveEvent.clientY - startY
      
      setFilePanelSize({
        width: Math.max(200, startWidth + deltaX),
        height: Math.max(200, startHeight + deltaY)
      })
    }
    
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [filePanelSize])

  const handleAiPanelResize = useCallback((e, direction) => {
    e.preventDefault()
    const startX = e.clientX
    const startY = e.clientY
    const startWidth = aiPanelSize.width
    const startHeight = aiPanelSize.height
    
    const handleMouseMove = (moveEvent) => {
      const deltaX = moveEvent.clientX - startX
      const deltaY = moveEvent.clientY - startY
      
      setAiPanelSize({
        width: Math.max(200, startWidth + deltaX),
        height: Math.max(200, startHeight + deltaY)
      })
    }
    
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [aiPanelSize])

  useEffect(() => {
    pollJobStatus()
  }, [pollJobStatus])

  const getNodeStyle = (type) => {
    switch (type) {
      case 'repo':
        return 'input'
      case 'file':
        return 'default'
      case 'class':
        return 'default'
      case 'function':
        return 'default'
      default:
        return 'default'
    }
  }

  const getEdgeColor = (type) => {
    switch (type) {
      case 'contains':
        return '#8b5cf6'
      case 'imports':
        return '#3b82f6'
      case 'extends':
        return '#10b981'
      case 'implements':
        return '#f59e0b'
      case 'calls':
        return '#ef4444'
      default:
        return '#6b7280'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-300">Loading graph...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-red-400 p-4">
          <p className="text-lg font-semibold mb-2">Error Loading Graph</p>
          <p className="text-sm">{error}</p>
          <p className="text-xs mt-2 text-gray-400">Please check the backend console for more details</p>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-slate-900/90 to-transparent p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {selectedNode && (
              <button
                onClick={handleBackToFullGraph}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg shadow-lg transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Full Graph</span>
              </button>
            )}
            <h2 className="text-xl font-bold text-white">
              Code Graph: {repoName}
            </h2>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleZoomIn}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-5 h-5" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            <button
              onClick={handleFitView}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
              title="Fit View"
            >
              <Maximize2 className="w-5 h-5" />
            </button>
            <button
              onClick={handleRotate}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
              title="Rotate View"
            >
              <RotateCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* File Content Panel */}
      {selectedNode && fileContent && (
        <div
          className="absolute z-10 bg-white/10 backdrop-blur-sm rounded-lg shadow-lg border border-white/20 flex flex-col overflow-hidden"
          style={{
            left: `${filePanelPos.x}px`,
            top: `${filePanelPos.y}px`,
            width: `${filePanelSize.width}px`,
            height: `${filePanelSize.height}px`
          }}
        >
          {/* Header */}
          <div
            className="p-3 border-b border-white/20 cursor-move flex items-center justify-between"
            onMouseDown={handleFilePanelDrag}
          >
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <GripVertical className="w-4 h-4 text-gray-400" />
              <File className="w-4 h-4 text-blue-400" />
              File Content
            </h3>
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-auto p-3">
            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono">
              {fileContent}
            </pre>
          </div>
          
          {/* Resize Handle */}
          <div
            className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
            onMouseDown={(e) => handleFilePanelResize(e, 'se')}
          >
            <GripVertical className="w-4 h-4 text-gray-400 rotate-45" />
          </div>
        </div>
      )}

      {/* AI Explanation Panel */}
      {selectedNode && (
        <div
          className="absolute z-10 bg-white/10 backdrop-blur-sm rounded-lg shadow-lg border border-white/20 flex flex-col overflow-hidden"
          style={{
            left: `${aiPanelPos.x}px`,
            top: `${aiPanelPos.y}px`,
            width: `${aiPanelSize.width}px`,
            height: `${aiPanelSize.height}px`
          }}
        >
          {/* Header */}
          <div
            className="p-3 border-b border-white/20 cursor-move flex items-center justify-between"
            onMouseDown={handleAiPanelDrag}
          >
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <GripVertical className="w-4 h-4 text-gray-400" />
              <Sparkles className="w-4 h-4 text-purple-400" />
              AI Explanation
            </h3>
            {!explanation && (
              <button
                onClick={handleExplainNode}
                disabled={isExplaining}
                className="flex items-center gap-1 px-2 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white text-xs rounded transition-colors"
              >
                {isExplaining ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Explaining...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3 h-3" />
                    <span>Explain</span>
                  </>
                )}
              </button>
            )}
          </div>
          
          {/* Chat Messages */}
          <div className="flex-1 overflow-auto p-3 space-y-3">
            {chatMessages.length === 0 && !explanation && (
              <p className="text-xs text-gray-500 italic">Click "Explain" to get AI-powered explanation of this node's functionality</p>
            )}
            {chatMessages.map((msg, index) => (
              <div
                key={index}
                className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                    msg.role === 'user' ? 'bg-purple-600' : 'bg-blue-600'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <User className="w-3 h-3 text-white" />
                  ) : (
                    <Bot className="w-3 h-3 text-white" />
                  )}
                </div>
                <div
                  className={`max-w-[80%] rounded-lg p-2 ${
                    msg.role === 'user'
                      ? 'bg-purple-600 text-white'
                      : 'bg-white/10 text-gray-100'
                  }`}
                >
                  <p className="text-xs whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-white/20">
                      <p className="text-xs text-gray-400 mb-1">Sources:</p>
                      <ul className="text-xs text-gray-300 space-y-1">
                        {msg.sources.map((source, idx) => (
                          <li key={idx}>• {source}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isChatLoading && (
              <div className="flex items-start gap-2">
                <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3 h-3 text-white" />
                </div>
                <div className="bg-white/10 rounded-lg p-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Chat Input */}
          <div className="p-3 border-t border-white/20">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleChatSend()}
                placeholder="Ask follow-up questions..."
                className="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-gray-400 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                disabled={isChatLoading}
              />
              <button
                onClick={handleChatSend}
                disabled={isChatLoading || !chatInput.trim()}
                className="px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Resize Handle */}
          <div
            className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
            onMouseDown={(e) => handleAiPanelResize(e, 'se')}
          >
            <GripVertical className="w-4 h-4 text-gray-400 rotate-45" />
          </div>
        </div>
      )}

      {/* Node Info Badge */}
      {selectedNode && (
        <div className="absolute top-4 right-4 z-10 bg-white/10 backdrop-blur-sm rounded-lg p-3 shadow-lg border border-white/20">
          <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
            {selectedNode.type === 'file' && <File className="w-4 h-4 text-blue-400" />}
            {selectedNode.type === 'class' && <Code2 className="w-4 h-4 text-green-400" />}
            {selectedNode.type === 'function' && <Database className="w-4 h-4 text-yellow-400" />}
            {selectedNode.type === 'repo' && <Folder className="w-4 h-4 text-purple-400" />}
            {selectedNode.label || selectedNode.data?.name || 'Node Details'}
          </h3>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-400">Type:</span>
              <span className="text-white capitalize">{selectedNode.type}</span>
            </div>
            {selectedNode.data?.path && (
              <div className="flex flex-col">
                <span className="text-gray-400">Path:</span>
                <span className="text-white text-xs break-all">{selectedNode.data.path}</span>
              </div>
            )}
            {selectedNode.data?.name && (
              <div className="flex justify-between">
                <span className="text-gray-400">Name:</span>
                <span className="text-white">{selectedNode.data.name}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeDragStart={handleNodeDragStart}
        onNodeDrag={handleNodeDrag}
        onNodeDragStop={handleNodeDragStop}
        fitView
        className="bg-slate-900"
      >
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            switch (node.type) {
              case 'input':
                return '#8b5cf6'
              case 'default':
                return '#3b82f6'
              default:
                return '#6b7280'
            }
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
          pannable={true}
          zoomable={true}
          position="bottom-right"
          style={{
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            border: '2px solid rgba(139, 92, 246, 0.3)',
            borderRadius: '8px'
          }}
        />
        <Background color="#ffffff" gap={16} />
      </ReactFlow>
    </div>
  )
}

export default GraphVisualization
