import { useState } from 'react'
import axios from 'axios'
import { Search, X, File, Code2, Activity } from 'lucide-react'

const FileSearch = ({ repoId, onResultClick }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [nodeTypeFilter, setNodeTypeFilter] = useState('all')
  const [showResults, setShowResults] = useState(false)

  const handleSearch = async (searchQuery) => {
    if (!searchQuery || !repoId) {
      setResults([])
      setShowResults(false)
      return
    }

    try {
      setLoading(true)
      const response = await axios.post(`http://localhost:8000/api/search-files/${repoId}`, {
        query: searchQuery,
        node_type: nodeTypeFilter !== 'all' ? nodeTypeFilter : null
      })
      setResults(response.data.results)
      setShowResults(true)
    } catch (err) {
      console.error('Error searching files:', err)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    setQuery(value)
    if (value.length > 0) {
      handleSearch(value)
    } else {
      setResults([])
      setShowResults(false)
    }
  }

  const handleResultClick = (result) => {
    if (onResultClick) {
      onResultClick(result)
    }
    setShowResults(false)
    setQuery('')
  }

  const clearSearch = () => {
    setQuery('')
    setResults([])
    setShowResults(false)
  }

  const getIconForType = (type) => {
    switch (type) {
      case 'file':
        return <File className="w-4 h-4 text-blue-400" />
      case 'class':
        return <Code2 className="w-4 h-4 text-purple-400" />
      case 'function':
        return <Activity className="w-4 h-4 text-green-400" />
      default:
        return <File className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <div className="relative">
      {/* Search Input */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={handleInputChange}
            placeholder="Search files, classes, functions..."
            className="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-10 py-2 text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 transition-colors"
          />
          {query && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Type Filter */}
        <select
          value={nodeTypeFilter}
          onChange={(e) => setNodeTypeFilter(e.target.value)}
          className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
        >
          <option value="all">All</option>
          <option value="file">Files</option>
          <option value="class">Classes</option>
          <option value="function">Functions</option>
        </select>
      </div>

      {/* Search Results */}
      {showResults && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white/10 backdrop-blur-md rounded-lg border border-white/20 shadow-xl max-h-96 overflow-y-auto z-50">
          {loading ? (
            <div className="p-4 text-center text-gray-400">
              Searching...
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-gray-400">
              No results found
            </div>
          ) : (
            <div className="p-2">
              {results.map((result) => (
                <div
                  key={result.id}
                  onClick={() => handleResultClick(result)}
                  className="flex items-center gap-3 p-3 hover:bg-white/10 rounded-lg cursor-pointer transition-colors"
                >
                  {getIconForType(result.type)}
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-medium truncate">
                      {result.label || result.name}
                    </div>
                    <div className="text-gray-400 text-sm truncate">
                      {result.path}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 capitalize">
                    {result.type}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FileSearch
