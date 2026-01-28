"use client"

import * as React from "react"
import { FileText, Upload, Trash2, Check, X, ChevronRight, Plus } from "lucide-react"
import { cn } from "@/lib/utils"
import { HomeworkUpload } from "@/components/homework-panel/HomeworkUpload"
import { homeworkService, type HomeworkItem } from "@/services/homework-service"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
} from "@/components/ui/card"
import HintButton from "@/components/hint-button/HintButton"
import { useHint } from "@/contexts/HintContext"

export interface BoundingBox {
  left: number   // percentage from left (0-100)
  top: number    // percentage from top (0-100)
  right: number  // percentage from left to right edge (0-100)
  bottom: number // percentage from top to bottom edge (0-100)
  page?: number  // page number for multi-page PDFs (0-indexed)
}

export interface HomeworkQuestion {
  id: string
  number: number
  text: string
  answered: boolean
  correct?: boolean
  bbox?: BoundingBox
}

// Helper to evaluate simple math expressions
const evaluateMathExpression = (expr: string): number | null => {
  try {
    // Remove "=" and anything after it
    const cleanExpr = expr.split('=')[0].trim()
    // Replace × and ÷ with * and /
    const normalized = cleanExpr
      .replace(/×/g, '*')
      .replace(/÷/g, '/')
      .replace(/x/gi, '*')
    // Only allow numbers and basic operators
    if (!/^[\d\s+\-*/().]+$/.test(normalized)) return null
    // Use Function constructor to safely evaluate
    const result = new Function(`return ${normalized}`)()
    return typeof result === 'number' && !isNaN(result) ? result : null
  } catch {
    return null
  }
}

interface HomeworkViewProps {
  onClose: () => void
  onQuestionsExtracted?: (questions: HomeworkQuestion[]) => void
  onQuestionIndexChange?: (index: number) => void
  currentQuestionIndex?: number
  onImageUrlChange?: (url: string | null) => void
  onFileTypeChange?: (type: string | null) => void
  onHomeworkIdChange?: (id: string | null) => void
  onPageInfoChange?: (currentPage: number, totalPages: number) => void
}

export function HomeworkView({ onClose, onQuestionsExtracted, onQuestionIndexChange, currentQuestionIndex: externalQuestionIndex, onImageUrlChange, onFileTypeChange, onHomeworkIdChange, onPageInfoChange }: HomeworkViewProps) {
  const [homeworkList, setHomeworkList] = React.useState<HomeworkItem[]>([])
  const [currentHomework, setCurrentHomework] = React.useState<HomeworkItem | null>(null)
  const [documentUrl, setDocumentUrl] = React.useState<string | null>(null)
  const [extractedQuestions, setExtractedQuestions] = React.useState<HomeworkQuestion[]>([])
  const [internalQuestionIndex, setInternalQuestionIndex] = React.useState(0)
  const [isLoading, setIsLoading] = React.useState(false)

  // Track which page's thumbnail is currently loaded (use ref to avoid effect loops)
  const loadedPageRef = React.useRef<number>(0)
  const [totalPages, setTotalPages] = React.useState(1)

  // Answer submission state
  const [userAnswer, setUserAnswer] = React.useState('')
  const [feedback, setFeedback] = React.useState<'correct' | 'incorrect' | null>(null)
  const [showingFeedback, setShowingFeedback] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  // Hint context
  const { showHints, setTotalHints } = useHint()

  // Generate hints for the current question
  const generateHints = (questionText: string) => {
    const match = questionText.match(/(\d+)\s*([+\-×÷xX*\/])\s*(\d+)/)
    if (match) {
      const num1 = parseInt(match[1])
      const num2 = parseInt(match[3])
      const operator = match[2]

      if (operator === '+' || operator === '×' || operator.toLowerCase() === 'x' || operator === '*') {
        return [
          `Start by counting from ${num1}, then add ${num2} more.`,
          `You can use your fingers: hold up ${num1} fingers, then count ${num2} more.`,
          `Think: ${num1} + ${num2} = ?`
        ]
      } else if (operator === '-') {
        return [
          `Start with ${num1}, then take away ${num2}.`,
          `Count backwards from ${num1}, ${num2} times.`,
          `Think: ${num1} - ${num2} = ?`
        ]
      }
    }
    return [`Try breaking down the problem step by step.`]
  }

  // Use external index if provided, otherwise use internal state
  const currentQuestionIndex = externalQuestionIndex ?? internalQuestionIndex
  const setCurrentQuestionIndex = (index: number) => {
    setInternalQuestionIndex(index)
    onQuestionIndexChange?.(index)
    // Reset answer state when changing questions
    setUserAnswer('')
    setFeedback(null)
    setShowingFeedback(false)
  }

  // Update total hints when question changes (must be after currentQuestionIndex is defined)
  React.useEffect(() => {
    const currentQuestion = extractedQuestions[currentQuestionIndex]
    if (currentQuestion) {
      const hints = generateHints(currentQuestion.text)
      setTotalHints(hints.length)
    }
  }, [currentQuestionIndex, extractedQuestions, setTotalHints])

  // Focus input when question changes
  React.useEffect(() => {
    if (inputRef.current && !showingFeedback) {
      inputRef.current.focus()
    }
  }, [currentQuestionIndex, showingFeedback])

  // Update thumbnail when question changes to a different page (for multi-page PDFs)
  React.useEffect(() => {
    const currentQuestion = extractedQuestions[currentQuestionIndex]
    if (!currentQuestion || !currentHomework) return

    const questionPage = currentQuestion.bbox?.page ?? 0
    const loadedPage = loadedPageRef.current

    console.log(`[HomeworkView] Question ${currentQuestionIndex + 1} "${currentQuestion.text}" is on page ${questionPage}, loaded thumbnail page: ${loadedPage}`)

    if (questionPage !== loadedPage) {
      console.log(`[HomeworkView] PAGE CHANGE NEEDED: ${loadedPage} -> ${questionPage}, loading new thumbnail`)

      // Update ref immediately to prevent duplicate loads
      loadedPageRef.current = questionPage

      // Notify parent about page change
      onPageInfoChange?.(questionPage, totalPages)

      // Load thumbnail for the new page
      homeworkService.getThumbnailBlob(currentHomework.homework_id, questionPage)
        .then(blob => {
          const url = URL.createObjectURL(blob)
          console.log(`[HomeworkView] Successfully loaded thumbnail for page ${questionPage}`)
          setDocumentUrl(prev => {
            if (prev) URL.revokeObjectURL(prev)
            return url
          })
        })
        .catch(err => {
          console.error('[HomeworkView] Failed to load page thumbnail:', err)
          // Reset ref so it can try again
          loadedPageRef.current = loadedPage
        })
    }
  }, [currentQuestionIndex, extractedQuestions, currentHomework, totalPages, onPageInfoChange])

  const handleSubmitAnswer = () => {
    if (!currentQuestion || !userAnswer.trim()) return

    // Evaluate the math expression to get expected answer
    const expectedAnswer = evaluateMathExpression(currentQuestion.text)
    const userNum = parseFloat(userAnswer.trim())

    if (expectedAnswer !== null && !isNaN(userNum)) {
      const isCorrect = Math.abs(expectedAnswer - userNum) < 0.001
      setFeedback(isCorrect ? 'correct' : 'incorrect')
      setShowingFeedback(true)

      // Update the question's answered status
      const updatedQuestions = extractedQuestions.map((q, i) =>
        i === currentQuestionIndex ? { ...q, answered: true, correct: isCorrect } : q
      )
      setExtractedQuestions(updatedQuestions)
      // Notify parent about the update
      onQuestionsExtracted?.(updatedQuestions)

      // Auto-advance after correct answer
      if (isCorrect) {
        setTimeout(() => {
          if (currentQuestionIndex < extractedQuestions.length - 1) {
            setCurrentQuestionIndex(currentQuestionIndex + 1)
          }
        }, 1500)
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !showingFeedback) {
      handleSubmitAnswer()
    }
  }

  // Fetch homework list on mount
  React.useEffect(() => {
    fetchHomeworkList()
  }, [])

  // Load document when currentHomework changes
  React.useEffect(() => {
    if (currentHomework) {
      loadDocument(currentHomework)
    }
    return () => {
      if (documentUrl) {
        URL.revokeObjectURL(documentUrl)
      }
    }
  }, [currentHomework])

  // Notify parent when document URL changes
  React.useEffect(() => {
    onImageUrlChange?.(documentUrl)
  }, [documentUrl, onImageUrlChange])

  // Notify parent when homework ID changes
  React.useEffect(() => {
    onHomeworkIdChange?.(currentHomework?.homework_id || null)
  }, [currentHomework, onHomeworkIdChange])

  // Notify parent when file type changes
  React.useEffect(() => {
    onFileTypeChange?.(currentHomework?.file_type || null)
  }, [currentHomework, onFileTypeChange])

  const fetchHomeworkList = async () => {
    console.log('[HomeworkView] fetchHomeworkList called')
    setIsLoading(true)
    try {
      const response = await homeworkService.listHomework()
      console.log('[HomeworkView] Fetched homework list:', response.homework_items.length, 'items')
      setHomeworkList(response.homework_items)

      // Auto-select the most recent homework
      if (response.homework_items.length > 0) {
        console.log('[HomeworkView] Auto-selecting first homework:', response.homework_items[0].homework_id)
        setCurrentHomework(response.homework_items[0])
      } else {
        console.log('[HomeworkView] No homework items found')
      }
    } catch (err) {
      console.error('[HomeworkView] Failed to fetch homework list:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadDocument = async (homework: HomeworkItem) => {
    console.log('[HomeworkView] loadDocument called for:', homework.homework_id)
    try {
      // Load the THUMBNAIL for sidebar display (works with CSS % positioning)
      // For PDFs, this returns a rendered PNG; for images, returns the original
      // Always start with page 0
      loadedPageRef.current = 0
      console.log('[HomeworkView] Fetching thumbnail for page 0...')
      const thumbnailBlob = await homeworkService.getThumbnailBlob(homework.homework_id, 0)
      const url = URL.createObjectURL(thumbnailBlob)
      setDocumentUrl(url)
      console.log('[HomeworkView] Loaded thumbnail for page 0 (initial load)')

      // Get homework details with extracted text
      const details = await homeworkService.getHomework(homework.homework_id)
      console.log('[HomeworkView] Homework details:', details)

      // Parse questions from extracted text
      if (details.extracted_text) {
        console.log('[HomeworkView] Raw extracted text:', details.extracted_text.substring(0, 500))
        const questions = parseQuestionsFromText(details.extracted_text)
        console.log('[HomeworkView] Parsed questions:', questions)
        console.log('[HomeworkView] Questions with bbox:', questions.filter(q => q.bbox).length, 'of', questions.length)
        setExtractedQuestions(questions)
        setCurrentQuestionIndex(0)

        // Calculate total pages from questions
        const pages = new Set(questions.map(q => q.bbox?.page ?? 0))
        const numPages = Math.max(...Array.from(pages)) + 1
        setTotalPages(numPages)
        console.log('[HomeworkView] Total pages:', numPages)

        // Notify parent about page info
        onPageInfoChange?.(0, numPages)

        // Notify parent component about extracted questions
        if (onQuestionsExtracted) {
          console.log('[HomeworkView] Calling onQuestionsExtracted with', questions.length, 'questions')
          onQuestionsExtracted(questions)
        }
      }
    } catch (err) {
      console.error('[HomeworkView] Failed to load document:', err)
    }
  }

  const parseQuestionsFromText = (text: string): HomeworkQuestion[] => {
    const questions: HomeworkQuestion[] = []
    const lines = text.split('\n').filter(line => line.trim())

    // Track current page from "--- Page X ---" markers
    let currentPage = 0

    // Track layout info per page (for fallback grid calculation)
    let layoutColumns = 2
    let layoutRows = 10
    let topMargin = 20
    let bottomMargin = 95

    // Layout regex: "LAYOUT: 2x10 starting at 20% from top, bottom at 95%"
    const layoutRegex = /LAYOUT:\s*(\d+)\s*x\s*(\d+)\s*starting\s*at\s*(\d+)%.*?(?:bottom\s*at\s*(\d+)%)?/i

    // Problem with BBOX: "PROBLEM 1: 3+4= | BBOX: 5%, 18%, 48%, 25%"
    const problemWithBboxRegex = /^PROBLEM\s*(\d+)\s*:\s*(.+?)\s*\|\s*BBOX:\s*([\d.]+)%?\s*,\s*([\d.]+)%?\s*,\s*([\d.]+)%?\s*,\s*([\d.]+)%?/i

    // Problem with grid position (legacy): "PROBLEM 1: 3+4= | POS: 1,1"
    const problemWithPosRegex = /^PROBLEM\s*(\d+)\s*:\s*(.+?)\s*\|\s*POS:\s*(\d+)\s*,\s*(\d+)/i

    // Fallback: "PROBLEM X:" without position
    const problemRegex = /^PROBLEM\s*(\d+)\s*:\s*(.+)$/i
    let foundProblems = false

    console.log('[parseQuestions] Parsing text:', text.substring(0, 500))

    for (const line of lines) {
      // Check for page markers
      const pageMatch = line.match(/---\s*Page\s*(\d+)\s*---/i)
      if (pageMatch) {
        currentPage = parseInt(pageMatch[1]) - 1 // Convert to 0-indexed
        continue
      }

      // Check for layout info
      const layoutMatch = line.match(layoutRegex)
      if (layoutMatch) {
        layoutColumns = parseInt(layoutMatch[1])
        layoutRows = parseInt(layoutMatch[2])
        // Add offset to topMargin since OCR tends to underestimate header size
        // Typical worksheet headers are 20-25% of page, not 15-18%
        topMargin = Math.max(22, parseInt(layoutMatch[3]) + 6)
        if (layoutMatch[4]) bottomMargin = parseInt(layoutMatch[4])
        console.log(`[parseQuestions] Layout: ${layoutColumns}x${layoutRows}, top: ${topMargin}% (adjusted), bottom: ${bottomMargin}%`)
        continue
      }

      // Try to match with direct BBOX coordinates (preferred)
      const bboxMatch = line.match(problemWithBboxRegex)
      if (bboxMatch) {
        foundProblems = true
        const num = parseInt(bboxMatch[1])
        const problemText = bboxMatch[2].trim()
        const left = parseFloat(bboxMatch[3])
        const top = parseFloat(bboxMatch[4])
        const right = parseFloat(bboxMatch[5])
        const bottom = parseFloat(bboxMatch[6])

        const bbox: BoundingBox = { left, top, right, bottom, page: currentPage }
        console.log(`[parseQuestions] Q${num}: "${problemText}" BBOX: ${left},${top},${right},${bottom}`)

        questions.push({
          id: `q-${num}`,
          number: num,
          text: problemText,
          answered: false,
          bbox
        })
        continue
      }

      // Try to match with grid position (legacy format)
      const posMatch = line.match(problemWithPosRegex)
      if (posMatch) {
        foundProblems = true
        const num = parseInt(posMatch[1])
        const problemText = posMatch[2].trim()
        const col = parseInt(posMatch[3])
        const row = parseInt(posMatch[4])

        // Calculate bounding box from grid position
        const marginX = 5
        const availableWidth = 100 - (2 * marginX)
        const availableHeight = bottomMargin - topMargin

        const cellWidth = availableWidth / layoutColumns
        const cellHeight = availableHeight / layoutRows

        const bbox: BoundingBox = {
          left: marginX + (col - 1) * cellWidth,
          top: topMargin + (row - 1) * cellHeight,
          right: marginX + col * cellWidth,
          bottom: topMargin + row * cellHeight,
          page: currentPage
        }

        console.log(`[parseQuestions] Q${num}: "${problemText}" POS: col=${col},row=${row} -> BBOX: ${bbox.left},${bbox.top},${bbox.right},${bbox.bottom}`)

        questions.push({
          id: `q-${num}`,
          number: num,
          text: problemText,
          answered: false,
          bbox
        })
        continue
      }

      // Fallback: match without position
      const match = line.match(problemRegex)
      if (match) {
        foundProblems = true
        const num = parseInt(match[1])
        const problemText = match[2].trim()
        questions.push({
          id: `q-${num}`,
          number: num,
          text: problemText,
          answered: false
        })
      }
    }

    if (foundProblems && questions.length > 0) {
      // Sort by page first, then by number within each page
      questions.sort((a, b) => {
        const pageA = a.bbox?.page ?? 0
        const pageB = b.bbox?.page ?? 0
        if (pageA !== pageB) return pageA - pageB
        return a.number - b.number
      })

      // Renumber questions sequentially across all pages
      const renumbered = questions.map((q, idx) => ({
        ...q,
        id: `q-${idx + 1}`,
        number: idx + 1
      }))

      // Log page distribution
      const page0Count = renumbered.filter(q => q.bbox?.page === 0).length
      const page1Count = renumbered.filter(q => q.bbox?.page === 1).length
      console.log(`[parseQuestions] Found ${renumbered.length} problems: ${page0Count} on page 0 (page 1), ${page1Count} on page 1 (page 2)`)
      console.log(`[parseQuestions] First question (Q1):`, renumbered[0]?.text, 'bbox:', renumbered[0]?.bbox)
      if (renumbered.length > 20) {
        console.log(`[parseQuestions] Question 21 (first on page 2):`, renumbered[20]?.text, 'bbox:', renumbered[20]?.bbox)
      }
      return renumbered
    }

    // Fallback: look for math equations
    let questionNumber = 0
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('[') || trimmed.length < 3) continue

      const isMathProblem = /\d+\s*[+\-×÷xX*\/]\s*\d+\s*=/.test(trimmed) ||
                           /\d+\s*[+\-]\s*\d+/.test(trimmed)

      if (isMathProblem) {
        questionNumber++
        questions.push({
          id: `q-${questionNumber}`,
          number: questionNumber,
          text: trimmed,
          answered: false
        })
      }
    }

    return questions
  }

  const handleFileUpload = async (file: File) => {
    try {
      const uploadResponse = await homeworkService.uploadHomework(file)
      console.log('[HomeworkView] Upload successful:', uploadResponse.homework_id)
      await fetchHomeworkList()
    } catch (err) {
      console.error('[HomeworkView] Upload failed:', err)
      throw err
    }
  }

  const handleDelete = async () => {
    if (!currentHomework) return
    try {
      const deletedId = currentHomework.homework_id
      await homeworkService.deleteHomework(deletedId)
      console.log('[HomeworkView] Deleted homework:', deletedId)

      // Find the next homework to load
      const remainingHomework = homeworkList.filter(h => h.homework_id !== deletedId)

      if (remainingHomework.length > 0) {
        // Load the next available homework
        setCurrentHomework(remainingHomework[0])
      } else {
        // No more homework, clear everything
        setCurrentHomework(null)
        setDocumentUrl(null)
        setExtractedQuestions([])
      }

      // Refresh the list
      await fetchHomeworkList()
      setShowAddUpload(false)
    } catch (err) {
      console.error('[HomeworkView] Delete failed:', err)
    }
  }

  const currentQuestion = extractedQuestions[currentQuestionIndex]

  console.log('[HomeworkView] Render state:', {
    currentHomework: currentHomework?.homework_id,
    extractedQuestions: extractedQuestions.length,
    currentQuestionIndex,
    isLoading
  })

  // No homework uploaded - show loading or empty state
  if (!currentHomework) {
    console.log('[HomeworkView] No currentHomework, isLoading:', isLoading)
    if (isLoading) {
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-xl font-bold">Loading homework...</div>
        </div>
      )
    }
    return <div className="h-full" />
  }

  // Homework loaded but no questions extracted
  if (extractedQuestions.length === 0) {
    console.log('[HomeworkView] No questions extracted yet')
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-xl font-bold">Processing homework...</div>
      </div>
    )
  }

  // Parse the question to extract numbers and operator for colored display
  const parseQuestion = (text: string) => {
    // Match patterns like "3+4=", "9 + 6 =", etc.
    const match = text.match(/(\d+)\s*([+\-×÷xX*\/])\s*(\d+)\s*=?/)
    if (match) {
      return {
        num1: match[1],
        operator: match[2].replace(/[xX*]/g, '+').replace(/\//g, '÷').replace(/-/g, '-'),
        num2: match[3]
      }
    }
    return null
  }

  const progressPercentage = extractedQuestions.length > 0
    ? ((currentQuestionIndex + 1) / extractedQuestions.length) * 100
    : 0

  // Homework loaded - show question in card style EXACTLY like homepage
  return (
    <div className="framework-perseus relative flex w-full h-full items-start justify-center px-3 md:px-4">
      {/* Neo-Brutalism Card - matches homepage exactly */}
      <Card className="relative flex w-full max-w-4xl md:max-w-5xl my-4 md:my-6 flex-col border-[4px] md:border-[5px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-200">
        {/* Progress bar at top */}
        <div className="absolute top-0 left-0 right-0 h-2 md:h-3 bg-[#FFFDF5] dark:bg-[#000000] border-b-[2px] md:border-b-[3px] border-black dark:border-white">
          <div
            className="h-full bg-[#C4B5FD] transition-all duration-500 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>

        <CardHeader className="space-y-2 pt-6 md:pt-7 px-4 md:px-6 border-b-[3px] md:border-b-[4px] border-black dark:border-white bg-[#FFD93D]">
          <div className="flex items-start justify-between gap-3 md:gap-4 flex-wrap">
            <div className="space-y-1.5 flex-1">
              {/* Breadcrumb Navigation */}
              <div className="flex items-center gap-2 flex-wrap text-xs md:text-sm font-bold text-black">
                <span className="uppercase tracking-wide">Question {currentQuestionIndex + 1} of {extractedQuestions.length}</span>
              </div>
            </div>

            {/* Neo-Brutalist Progress Badge */}
            <div className="flex items-center gap-2 md:gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-[10px] md:text-xs font-black uppercase tracking-wider text-black mb-0.5">
                  Progress
                </div>
                <div className="text-xs md:text-sm font-black text-black">
                  Q <span className="text-[#FF6B6B]">{currentQuestionIndex + 1}</span>/{extractedQuestions.length}
                </div>
              </div>
              <div className="px-3 md:px-4 py-2 md:py-3 border-[2px] md:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
                <div className="text-xl md:text-2xl font-black text-black dark:text-white">
                  {Math.round(progressPercentage)}%
                </div>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="px-4 md:px-6 py-4 md:py-6 bg-[#FFFDF5] dark:bg-[#000000]">
          <div className="relative w-full max-w-4xl mx-auto">
            {currentQuestion ? (
              <div className="py-4">
                {/* Instruction - Dynamic based on question */}
                <div className="text-lg md:text-xl font-bold text-black dark:text-white mb-6">
                  {currentQuestion.text.includes('count') || currentQuestion.text.includes('Count') ?
                    'Count and Add.' :
                    currentQuestion.text.includes('+') ? 'Add.' :
                    currentQuestion.text.includes('-') ? 'Subtract.' :
                    currentQuestion.text.includes('×') || currentQuestion.text.includes('*') || currentQuestion.text.toLowerCase().includes('x') ? 'Multiply.' :
                    currentQuestion.text.includes('÷') || currentQuestion.text.includes('/') ? 'Divide.' :
                    'Solve.'}
                </div>

                {/* The Equation with inline input */}
                <div className="flex items-center gap-3 md:gap-4 flex-wrap">
                  {(() => {
                    const parsed = parseQuestion(currentQuestion.text)
                    if (parsed) {
                      return (
                        <>
                          <span className="text-5xl md:text-6xl lg:text-7xl font-light text-[#4A90D9]">
                            {parsed.num1}
                          </span>
                          <span className="text-5xl md:text-6xl lg:text-7xl font-light text-black dark:text-white">
                            {parsed.operator}
                          </span>
                          <span className="text-5xl md:text-6xl lg:text-7xl font-light text-[#E91E63]">
                            {parsed.num2}
                          </span>
                          <span className="text-5xl md:text-6xl lg:text-7xl font-light text-black dark:text-white">
                            =
                          </span>
                          {/* Inline answer input */}
                          {showingFeedback ? (
                            <div className={cn(
                              "min-w-[100px] md:min-w-[120px] h-[60px] md:h-[80px] border-[3px] rounded-lg flex items-center justify-center text-4xl md:text-5xl font-light",
                              feedback === 'correct'
                                ? "border-green-500 bg-green-100 text-green-600"
                                : "border-[#FF6B6B] bg-red-100 text-[#FF6B6B]"
                            )}>
                              {userAnswer}
                            </div>
                          ) : (
                            <input
                              ref={inputRef}
                              type="text"
                              value={userAnswer}
                              onChange={(e) => setUserAnswer(e.target.value)}
                              onKeyDown={handleKeyDown}
                              className="w-[100px] md:w-[120px] h-[60px] md:h-[80px] text-4xl md:text-5xl font-light text-center border-[3px] border-black dark:border-white rounded-lg focus:outline-none focus:border-[#4A90D9] bg-white dark:bg-[#1a1a1a]"
                            />
                          )}
                        </>
                      )
                    }
                    // Fallback for non-math questions
                    return (
                      <span className="text-3xl md:text-4xl font-bold text-black dark:text-white">
                        {currentQuestion.text}
                      </span>
                    )
                  })()}
                </div>

                {/* Feedback message */}
                {showingFeedback && (
                  <div className={cn(
                    "mt-6 flex items-center gap-3 text-xl font-bold",
                    feedback === 'correct' ? "text-green-600" : "text-[#FF6B6B]"
                  )}>
                    {feedback === 'correct' ? (
                      <>
                        <Check className="w-6 h-6" />
                        <span>Correct!</span>
                      </>
                    ) : (
                      <>
                        <X className="w-6 h-6" />
                        <span>Not quite. Try again!</span>
                      </>
                    )}
                  </div>
                )}

                {/* Hint Display for Homework */}
                {showHints && currentQuestion && (
                  <div className="mt-4 md:mt-6 border-[3px] md:border-[4px] border-black dark:border-white bg-[#FFE500] dark:bg-[#FFD93D] shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
                    <div className="p-4 md:p-5">
                      <div className="flex items-center gap-2 md:gap-3 mb-3 pb-2 border-b-[2px] border-black">
                        <div className="p-1.5 border-[2px] border-black bg-[#FFFDF5]">
                          <span className="text-lg">💡</span>
                        </div>
                        <h3 className="text-sm font-black text-black uppercase tracking-tight">
                          Hint
                        </h3>
                      </div>
                      <div className="bg-white p-3 border-[2px] border-black">
                        {generateHints(currentQuestion.text).map((hint, idx) => (
                          <p key={idx} className="text-sm md:text-base text-black mb-2 last:mb-0">
                            • {hint}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-400 text-lg py-8 text-center">Loading questions...</div>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex justify-between items-center gap-2 md:gap-3 px-4 md:px-6 pb-4 md:pb-5 pt-3 md:pt-4 border-t-[3px] md:border-t-[4px] border-black dark:border-white bg-white dark:bg-neutral-900">
          {/* HINT button - uses HintContext */}
          <HintButton inline={true} />

          {/* Right side buttons */}
          <div className="flex gap-2 md:gap-3">
            {showingFeedback && feedback === 'incorrect' && (
              <Button
                type="button"
                size="sm"
                onClick={() => {
                  setFeedback(null)
                  setShowingFeedback(false)
                  setUserAnswer('')
                }}
                className="border-[2px] md:border-[3px] border-black bg-[#FFD93D] hover:bg-[#FFE566] text-black font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] transition-all"
              >
                Try Again
              </Button>
            )}
            {!showingFeedback && (
              <Button
                type="button"
                size="sm"
                onClick={handleSubmitAnswer}
                disabled={!userAnswer.trim()}
                className="border-[2px] md:border-[3px] border-black bg-[#4ECDC4] hover:bg-[#45B7AA] text-white font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] transition-all disabled:opacity-50"
              >
                Submit
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setCurrentQuestionIndex(Math.min(extractedQuestions.length - 1, currentQuestionIndex + 1))}
              disabled={currentQuestionIndex === extractedQuestions.length - 1}
              className="border-[2px] md:border-[3px] border-black bg-[#FFD93D] hover:bg-[#FFE566] text-black font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] transition-all disabled:opacity-50"
            >
              Next →
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}

export default HomeworkView
