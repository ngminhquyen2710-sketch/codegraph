import { useState, useEffect } from 'react'
import axios from 'axios'
import { X, ChevronRight, ChevronLeft, Lightbulb, Play, SkipForward, Loader2 } from 'lucide-react'

const InteractiveTour = ({ repoId, repoName, onStartTour, onFileClick }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [isActive, setIsActive] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [loading, setLoading] = useState(false)
  const [tourSteps, setTourSteps] = useState([])
  const [learningPathData, setLearningPathData] = useState(null)

  const fetchLearningPath = async () => {
    if (!repoId) return
    
    try {
      setLoading(true)
      
      // First fetch repo summary
      let repoSummary = ""
      try {
        const summaryResponse = await axios.get(`http://localhost:8000/api/repo-summary/${repoId}`)
        repoSummary = summaryResponse.data.summary
      } catch (err) {
        console.error('Error fetching repo summary:', err)
        repoSummary = `This is the ${repoName || 'repository'} codebase. Let me help you understand its structure and functionality.`
      }
      
      // Then fetch learning path
      const response = await axios.post(`http://localhost:8000/api/generate-learning-path/${repoId}`)
      setLearningPathData(response.data)
      
      // Build tour steps from learning path
      const steps = [
        {
          title: "Repository Overview �",
          content: repoSummary,
          highlight: null,
          files_to_examine: []
        },
        ...response.data.learning_path.map(step => ({
          title: step.title,
          content: step.content,
          highlight: step.highlight,
          files_to_examine: step.files_to_examine || []
        })),
        {
          title: "You're All Set! 🎉",
          content: "You now have a personalized learning path. Start exploring the repository by following the steps above. You can always ask questions using the AI chat for more details.",
          highlight: null,
          files_to_examine: []
        }
      ]
      
      setTourSteps(steps)
    } catch (err) {
      console.error('Error fetching learning path:', err)
      // Fallback to default steps
      setTourSteps([
        {
          title: "Repository Overview �",
          content: `This is the ${repoName || 'repository'} codebase. Let me help you understand its structure and functionality.`,
          highlight: null,
          files_to_examine: []
        },
        {
          title: "Repository Overview",
          content: "The Overview Dashboard shows key statistics: total files, classes, functions, lines of code, and complexity score.",
          highlight: "overview",
          files_to_examine: []
        },
        {
          title: "Project Structure",
          content: "The Project Tree shows the file and folder structure. You can expand/collapse folders and click on files to view their contents.",
          highlight: "tree",
          files_to_examine: []
        },
        {
          title: "Code Graph Visualization",
          content: "The interactive graph shows relationships between files, classes, and functions. You can zoom, pan, and click on nodes.",
          highlight: "graph",
          files_to_examine: []
        },
        {
          title: "AI-Powered Chat",
          content: "Ask questions about the codebase using the AI chat. The system uses graph-aware retrieval to provide accurate answers.",
          highlight: "chat",
          files_to_examine: []
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleNext = () => {
    if (currentStep < tourSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleEndTour()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleEndTour = () => {
    setIsActive(false)
    setCurrentStep(0)
    if (onStartTour) {
      onStartTour(false)
    }
  }

  const handleStartTour = async () => {
    setIsActive(true)
    setCurrentStep(0)
    await fetchLearningPath()
    if (onStartTour) {
      onStartTour(true)
    }
  }

  const handleSkip = () => {
    handleEndTour()
  }

  if (!isActive && !isMinimized) {
    return (
      <div className="fixed bottom-6 left-6 z-50">
        <button
          onClick={handleStartTour}
          className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-6 py-3 rounded-full shadow-lg flex items-center gap-2 transition-all hover:scale-105"
        >
          <Play className="w-5 h-5" />
          <span className="font-medium">Start AI-Powered Tour</span>
        </button>
      </div>
    )
  }

  if (!isActive && isMinimized) {
    return (
      <div className="fixed bottom-6 left-6 z-50">
        <button
          onClick={handleStartTour}
          className="bg-white/10 backdrop-blur-sm hover:bg-white/20 text-white px-4 py-2 rounded-full shadow-lg border border-white/20 flex items-center gap-2 transition-all"
        >
          <Lightbulb className="w-4 h-4" />
          <span className="text-sm">Show Tour</span>
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="fixed bottom-6 left-6 right-6 md:left-auto md:right-6 md:w-96 z-50">
        <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-2xl border border-white/20 overflow-hidden">
          <div className="p-6 flex flex-col items-center justify-center">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-4" />
            <p className="text-white">Analyzing repository and creating your personalized learning path...</p>
          </div>
        </div>
      </div>
    )
  }

  if (tourSteps.length === 0) {
    return null
  }

  const currentTourStep = tourSteps[currentStep]

  return (
    <div className="fixed bottom-6 left-6 right-6 md:left-auto md:right-6 md:w-96 z-50">
      <div className="bg-white/10 backdrop-blur-md rounded-xl shadow-2xl border border-white/20 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600/50 to-blue-600/50 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-300" />
            <h3 className="text-white font-semibold">Interactive Tour</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMinimized(true)}
              className="text-white/70 hover:text-white transition-colors"
              title="Minimize"
            >
              <SkipForward className="w-4 h-4" />
            </button>
            <button
              onClick={handleEndTour}
              className="text-white/70 hover:text-white transition-colors"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <h4 className="text-xl font-bold text-white mb-3">{currentTourStep.title}</h4>
          <p className="text-gray-300 leading-relaxed mb-4">{currentTourStep.content}</p>

          {/* Files to Examine */}
          {currentTourStep.files_to_examine && currentTourStep.files_to_examine.length > 0 && (
            <div className="mb-4">
              <p className="text-gray-400 text-sm mb-2">Files to examine:</p>
              <div className="space-y-1">
                {currentTourStep.files_to_examine.map((file, idx) => (
                  <button
                    key={idx}
                    onClick={() => onFileClick && onFileClick(file)}
                    className="w-full text-left bg-white/5 hover:bg-white/10 rounded px-3 py-2 text-sm text-gray-300 transition-colors flex items-center justify-between group"
                  >
                    <span>{file}</span>
                    <span className="text-xs text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      View in graph →
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Progress */}
          <div className="flex items-center gap-2 mb-4">
            <div className="flex-1 bg-white/10 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${((currentStep + 1) / tourSteps.length) * 100}%` }}
              ></div>
            </div>
            <span className="text-gray-400 text-sm">
              {currentStep + 1}/{tourSteps.length}
            </span>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <button
              onClick={handlePrevious}
              disabled={currentStep === 0}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            <button
              onClick={handleSkip}
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Skip Tour
            </button>

            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white transition-all"
            >
              {currentStep === tourSteps.length - 1 ? 'Finish' : 'Next'}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default InteractiveTour
