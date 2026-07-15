import { useState, useEffect } from 'react'
import axios from 'axios'
import { File, Code2, Database, Activity, Clock, Globe } from 'lucide-react'

const RepoOverview = ({ repoId, repoName }) => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (repoId) {
      fetchRepoOverview()
    }
  }, [repoId])

  const fetchRepoOverview = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`http://localhost:8000/api/repo-overview/${repoId}`)
      setStats(response.data)
      setError(null)
    } catch (err) {
      console.error('Error fetching repo overview:', err)
      setError('Failed to load repository overview')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-white/20 rounded w-1/3"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-white/20 rounded"></div>
            ))}
          </div>
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

  if (!stats) {
    return null
  }

  const { stats: repoStats, last_updated } = stats

  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
        <Database className="w-6 h-6" />
        Repository Overview: {repoName}
      </h2>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Files */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <File className="w-5 h-5 text-blue-400" />
            <span className="text-gray-400 text-sm">Total Files</span>
          </div>
          <p className="text-3xl font-bold text-white">{repoStats.total_files}</p>
        </div>

        {/* Total Classes */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <Code2 className="w-5 h-5 text-purple-400" />
            <span className="text-gray-400 text-sm">Total Classes</span>
          </div>
          <p className="text-3xl font-bold text-white">{repoStats.total_classes}</p>
        </div>

        {/* Total Functions */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="w-5 h-5 text-green-400" />
            <span className="text-gray-400 text-sm">Total Functions</span>
          </div>
          <p className="text-3xl font-bold text-white">{repoStats.total_functions}</p>
        </div>

        {/* Lines of Code */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <Database className="w-5 h-5 text-yellow-400" />
            <span className="text-gray-400 text-sm">Lines of Code</span>
          </div>
          <p className="text-3xl font-bold text-white">{repoStats.lines_of_code.toLocaleString()}</p>
        </div>
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Languages */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-3 mb-3">
            <Globe className="w-5 h-5 text-cyan-400" />
            <span className="text-gray-400 text-sm font-medium">Languages</span>
          </div>
          <div className="space-y-2">
            {Object.entries(repoStats.languages).map(([lang, count]) => (
              <div key={lang} className="flex justify-between items-center">
                <span className="text-white">{lang}</span>
                <span className="text-gray-400 text-sm">{count} files</span>
              </div>
            ))}
          </div>
        </div>

        {/* Complexity Score */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-3 mb-3">
            <Activity className="w-5 h-5 text-orange-400" />
            <span className="text-gray-400 text-sm font-medium">Complexity Score</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 rounded-full h-2">
              <div 
                className="bg-orange-400 h-2 rounded-full transition-all"
                style={{ width: `${Math.min(repoStats.complexity_score * 10, 100)}%` }}
              ></div>
            </div>
            <span className="text-white font-bold">{repoStats.complexity_score}</span>
          </div>
          <p className="text-gray-400 text-xs mt-2">
            {repoStats.complexity_score < 5 ? 'Low complexity' : 
             repoStats.complexity_score < 10 ? 'Medium complexity' : 'High complexity'}
          </p>
        </div>

        {/* Last Updated */}
        <div className="bg-white/5 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-3 mb-3">
            <Clock className="w-5 h-5 text-pink-400" />
            <span className="text-gray-400 text-sm font-medium">Last Updated</span>
          </div>
          <p className="text-white">{last_updated}</p>
        </div>
      </div>
    </div>
  )
}

export default RepoOverview
