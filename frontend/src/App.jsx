import { useState } from 'react'
import { Github, Loader2, MessageSquare, Network, RotateCcw, X, Layout, Folder } from 'lucide-react'
import { ReactFlowProvider } from 'reactflow'
import RepoInput from './components/RepoInput'
import GraphVisualization from './components/GraphVisualization'
import ChatBox from './components/ChatBox'
import RepoOverview from './components/RepoOverview'
import ProjectTree from './components/ProjectTree'
import InteractiveTour from './components/InteractiveTour'
import FileSearch from './components/FileSearch'

function App() {
  const [repoId, setRepoId] = useState(null)
  const [repoName, setRepoName] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [showGraph, setShowGraph] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [isChatExpanded, setIsChatExpanded] = useState(false)
  const [showOverview, setShowOverview] = useState(false)
  const [showTree, setShowTree] = useState(false)
  const [highlightNodePath, setHighlightNodePath] = useState(null)

  const handleRepoSubmit = (jobId) => {
    setRepoId(jobId)
    setIsProcessing(true)
    setShowGraph(true)  // Show graph container immediately
    setShowChat(false)
  }

  const handleProcessingComplete = (name) => {
    setIsProcessing(false)
    setRepoName(name)
    setShowChat(true)
    setShowOverview(true)  // Auto-show overview after processing
  }

  const toggleChat = () => {
    setIsChatExpanded(!isChatExpanded)
  }

  const toggleOverview = () => {
    setShowOverview(!showOverview)
  }

  const toggleTree = () => {
    setShowTree(!showTree)
  }

  const handleFileClick = (nodeId) => {
    console.log('File clicked:', nodeId)
  }

  const handleSearchResultClick = (result) => {
    console.log('Search result clicked:', result)
    // Could highlight the node in the graph or show details
  }

  const handleTourFileClick = (filePath) => {
    console.log('Tour file clicked:', filePath)
    setHighlightNodePath(filePath)
  }

  const handleReset = () => {
    setRepoId(null)
    setRepoName('')
    setIsProcessing(false)
    setShowGraph(false)
    setShowChat(false)
    setShowOverview(false)
    setShowTree(false)
    setHighlightNodePath(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 bg-white/5 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Network className="w-8 h-8 text-purple-400" />
              <h1 className="text-2xl font-bold text-white">CodeExplorer AI</h1>
              <span className="text-sm text-purple-300">Repository Graph Explorer</span>
            </div>
            {repoId && (
              <div className="flex items-center gap-2">
                <div className="w-64">
                  <FileSearch repoId={repoId} onResultClick={handleSearchResultClick} />
                </div>
                <button
                  onClick={toggleOverview}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${showOverview ? 'bg-purple-500/30 text-purple-300' : 'bg-white/10 text-gray-300 hover:bg-white/20'}`}
                >
                  <Layout className="w-4 h-4" />
                  <span>Overview</span>
                </button>
                <button
                  onClick={toggleTree}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${showTree ? 'bg-purple-500/30 text-purple-300' : 'bg-white/10 text-gray-300 hover:bg-white/20'}`}
                >
                  <Folder className="w-4 h-4" />
                  <span>Tree</span>
                </button>
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded-lg transition-colors"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Reset</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {!repoId && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <Github className="w-16 h-16 mx-auto mb-4 text-purple-400" />
              <h2 className="text-3xl font-bold text-white mb-2">
                Explore Code with AI
              </h2>
              <p className="text-gray-300">
                Paste a GitHub repository URL to visualize its code graph and interact with it using AI
              </p>
            </div>
            <RepoInput onSubmit={handleRepoSubmit} />
          </div>
        )}

        {isProcessing && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-8 text-center">
              <Loader2 className="w-16 h-16 mx-auto mb-4 text-purple-400 animate-spin" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Processing Repository
              </h3>
              <p className="text-gray-300">
                Cloning repository, building code graph, and generating embeddings...
              </p>
            </div>
          </div>
        )}

        {showGraph && (
          <div className="relative h-screen">
            {/* Overview Panel */}
            {showOverview && (
              <div className="absolute top-4 left-4 right-4 z-40">
                <RepoOverview repoId={repoId} repoName={repoName} />
              </div>
            )}

            {/* Project Tree Panel */}
            {showTree && (
              <div className="absolute top-4 right-4 w-80 z-40">
                <ProjectTree repoId={repoId} repoName={repoName} onFileClick={handleFileClick} />
              </div>
            )}

            {/* Graph Visualization - Full Screen */}
            <div className="absolute inset-0">
              <ReactFlowProvider>
                <GraphVisualization repoId={repoId} onLoaded={handleProcessingComplete} repoName={repoName} highlightNodePath={highlightNodePath} />
              </ReactFlowProvider>
            </div>

            {/* Floating Chat Button / Expanded Chat Box */}
            {showChat && (
              <>
                {/* Collapsed Chat Button */}
                {!isChatExpanded && (
                  <button
                    onClick={toggleChat}
                    className="fixed bottom-6 right-6 w-14 h-14 bg-purple-600 hover:bg-purple-700 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-110 z-50"
                    title="Open AI Chat"
                  >
                    <MessageSquare className="w-6 h-6 text-white" />
                  </button>
                )}

                {/* Expanded Chat Box */}
                {isChatExpanded && (
                  <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-white/10 backdrop-blur-sm rounded-lg shadow-2xl z-50 flex flex-col">
                    {/* Chat Header */}
                    <div className="flex items-center justify-between p-4 border-b border-white/10">
                      <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <MessageSquare className="w-5 h-5" />
                        AI Chat
                      </h3>
                      <button
                        onClick={toggleChat}
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                    {/* Chat Content */}
                    <div className="flex-1 overflow-hidden">
                      <ChatBox repoId={repoId} />
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Interactive Tour */}
            <InteractiveTour repoId={repoId} repoName={repoName} onFileClick={handleTourFileClick} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
