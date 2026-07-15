import { useState, useEffect } from 'react'
import axios from 'axios'
import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from 'lucide-react'

const ProjectTree = ({ repoId, repoName, onFileClick }) => {
  const [tree, setTree] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedNodes, setExpandedNodes] = useState(new Set())

  useEffect(() => {
    if (repoId) {
      fetchProjectStructure()
    }
  }, [repoId])

  const fetchProjectStructure = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`http://localhost:8000/api/project-structure/${repoId}`)
      setTree(response.data.tree)
      setError(null)
      // Auto-expand first level
      if (response.data.tree) {
        const firstLevelKeys = Object.keys(response.data.tree)
        setExpandedNodes(new Set(firstLevelKeys))
      }
    } catch (err) {
      console.error('Error fetching project structure:', err)
      setError('Failed to load project structure')
    } finally {
      setLoading(false)
    }
  }

  const toggleNode = (nodePath) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(nodePath)) {
      newExpanded.delete(nodePath)
    } else {
      newExpanded.add(nodePath)
    }
    setExpandedNodes(newExpanded)
  }

  const renderTreeNode = (node, path = '', level = 0) => {
    const isExpanded = expandedNodes.has(path)
    const isFile = node.type === 'file'
    const paddingLeft = level * 16

    if (isFile) {
      return (
        <div key={path} className="flex items-center gap-2 py-1 hover:bg-white/10 rounded cursor-pointer" style={{ paddingLeft: `${paddingLeft}px` }} onClick={() => onFileClick && onFileClick(node.node_id)}>
          <File className="w-4 h-4 text-blue-400" />
          <span className="text-gray-300 text-sm">{node.name}</span>
        </div>
      )
    }

    const children = Object.values(node.children || {})
    const hasChildren = children.length > 0

    return (
      <div key={path}>
        <div 
          className="flex items-center gap-2 py-1 hover:bg-white/10 rounded cursor-pointer"
          style={{ paddingLeft: `${paddingLeft}px` }}
          onClick={() => hasChildren && toggleNode(path)}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )
          ) : (
            <div className="w-4 h-4" />
          )}
          {isExpanded ? (
            <FolderOpen className="w-4 h-4 text-yellow-400" />
          ) : (
            <Folder className="w-4 h-4 text-yellow-400" />
          )}
          <span className="text-gray-300 text-sm">{node.name}</span>
          {hasChildren && (
            <span className="text-gray-500 text-xs ml-auto">{children.length}</span>
          )}
        </div>
        {isExpanded && hasChildren && (
          <div>
            {children.map((child) => 
              renderTreeNode(child, `${path}/${child.name}`, level + 1)
            )}
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-white/20 rounded w-1/3"></div>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-4 bg-white/20 rounded" style={{ marginLeft: `${i * 8}px` }}></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-500/10 backdrop-blur-sm rounded-lg p-6 border border-red-500/20">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  if (!tree) {
    return null
  }

  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
      <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
        <Folder className="w-5 h-5" />
        Project Structure: {repoName}
      </h2>
      <div className="max-h-96 overflow-y-auto">
        {Object.entries(tree).map(([name, node]) => 
          renderTreeNode(node, name, 0)
        )}
      </div>
    </div>
  )
}

export default ProjectTree
