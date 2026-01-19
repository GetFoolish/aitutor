"use client"

import * as React from "react"
import { FileText, Image as ImageIcon, File, Trash2, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { HomeworkUpload } from "./HomeworkUpload"
import { homeworkService, type HomeworkItem } from "@/services/homework-service"
import { useTutorContext } from "@/features/tutor/TutorContext"

interface HomeworkPanelProps {
  className?: string
}

const HomeworkPanel = React.forwardRef<HTMLDivElement, HomeworkPanelProps>(
  ({ className }, ref) => {
    const [homeworkList, setHomeworkList] = React.useState<HomeworkItem[]>([])
    const [isLoading, setIsLoading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)
    const [previewOpen, setPreviewOpen] = React.useState(false)
    const [previewItem, setPreviewItem] = React.useState<HomeworkItem | null>(null)
    const [previewUrl, setPreviewUrl] = React.useState<string | null>(null)
    const [thumbnailUrls, setThumbnailUrls] = React.useState<Record<string, string>>({})

    // Get tutor context to inject homework
    const { client: tutorClient, connected: tutorConnected } = useTutorContext()
    const [pendingHomeworkId, setPendingHomeworkId] = React.useState<string | null>(null)

    // When tutor connects, send any pending homework
    React.useEffect(() => {
      let cancelled = false

      const sendPendingHomework = async () => {
        if (tutorConnected && homeworkList.length > 0) {
          // Wait for connection to stabilize before sending homework
          console.log('[Homework] Tutor connected, waiting for connection to stabilize...')
          await new Promise(resolve => setTimeout(resolve, 1500))

          if (cancelled) return

          // Send the most recent homework to the tutor
          const latestHomework = homeworkList[0]
          console.log('[Homework] Sending homework to tutor:', latestHomework.filename)

          try {
            const homeworkDetails = await homeworkService.getHomework(latestHomework.homework_id)
            if (cancelled) return

            if (homeworkDetails.extracted_text) {
              console.log('[Homework] Got extracted text, injecting into tutor context...')
              await tutorClient.injectHomeworkContext(
                homeworkDetails.extracted_text,
                homeworkDetails.filename
              )
              console.log('[Homework] Successfully sent homework to tutor:', homeworkDetails.filename)
            } else {
              console.warn('[Homework] No extracted text found for:', latestHomework.filename)
            }
          } catch (err) {
            console.error('[Homework] Could not send homework to tutor:', err)
          }
        }
      }

      sendPendingHomework()

      return () => {
        cancelled = true
      }
    }, [tutorConnected, homeworkList])

    // Fetch homework list on mount
    React.useEffect(() => {
      fetchHomeworkList()
    }, [])

    // Load thumbnails for images and PDFs
    React.useEffect(() => {
      const loadThumbnails = async () => {
        const urls: Record<string, string> = {}

        for (const item of homeworkList) {
          if (item.file_type === 'image' || item.file_type === 'pdf') {
            try {
              const blob = await homeworkService.getFileBlob(item.homework_id)
              const url = URL.createObjectURL(blob)
              urls[item.homework_id] = url
            } catch (err) {
              // Ignore errors for individual thumbnails
            }
          }
        }

        setThumbnailUrls(urls)
      }

      if (homeworkList.length > 0) {
        loadThumbnails()
      }

      return () => {
        Object.values(thumbnailUrls).forEach(url => URL.revokeObjectURL(url))
      }
    }, [homeworkList])

    // Cleanup preview URL when preview closes
    React.useEffect(() => {
      if (!previewOpen && previewUrl) {
        URL.revokeObjectURL(previewUrl)
        setPreviewUrl(null)
      }
    }, [previewOpen])

    const fetchHomeworkList = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const response = await homeworkService.listHomework()
        setHomeworkList(response.homework_items)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load homework')
      } finally {
        setIsLoading(false)
      }
    }

    const handlePreviewClick = async (item: HomeworkItem, e: React.MouseEvent) => {
      e.stopPropagation()

      if (item.file_type !== 'image' && item.file_type !== 'pdf') {
        return
      }

      try {
        let url = thumbnailUrls[item.homework_id]
        if (!url) {
          const blob = await homeworkService.getFileBlob(item.homework_id)
          url = URL.createObjectURL(blob)
        }

        setPreviewItem(item)
        setPreviewUrl(url)
        setPreviewOpen(true)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load preview')
      }
    }

    const handleFileUpload = async (file: File) => {
      try {
        // Upload the file
        console.log('[Homework] Uploading file:', file.name)
        const uploadResponse = await homeworkService.uploadHomework(file)
        console.log('[Homework] Upload successful, homework_id:', uploadResponse.homework_id)
        await fetchHomeworkList()

        // If tutor is connected, send homework content to it
        console.log('[Homework] Tutor connected:', tutorConnected, 'homework_id:', uploadResponse.homework_id)
        if (tutorConnected && uploadResponse.homework_id) {
          try {
            // Fetch the homework details to get extracted text
            console.log('[Homework] Fetching homework details...')
            const homeworkDetails = await homeworkService.getHomework(uploadResponse.homework_id)
            console.log('[Homework] Got details, extracted_text length:', homeworkDetails.extracted_text?.length || 0)

            if (homeworkDetails.extracted_text) {
              console.log('[Homework] Injecting homework into tutor context...')
              const success = await tutorClient.injectHomeworkContext(
                homeworkDetails.extracted_text,
                homeworkDetails.filename
              )
              if (success) {
                console.log('[Homework] Successfully sent to tutor:', homeworkDetails.filename)
              } else {
                console.warn('[Homework] Failed to send to tutor after retries')
              }
            } else {
              console.warn('[Homework] No extracted text available for:', homeworkDetails.filename)
            }
          } catch (detailsErr) {
            console.error('[Homework] Could not send homework to tutor:', detailsErr)
            // Don't fail the upload if we can't send to tutor
          }
        }
      } catch (err) {
        throw err
      }
    }

    const handleDeleteHomework = async (homeworkId: string, e: React.MouseEvent) => {
      e.stopPropagation()

      if (!confirm('Delete this homework?')) {
        return
      }

      try {
        await homeworkService.deleteHomework(homeworkId)
        await fetchHomeworkList()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete homework')
      }
    }

    const getFileIcon = (item: HomeworkItem) => {
      const thumbnailUrl = thumbnailUrls[item.homework_id]

      if (item.file_type === 'image' && thumbnailUrl) {
        return (
          <div
            className="w-10 h-10 rounded border-[2px] border-black overflow-hidden cursor-pointer hover:border-[#FFD93D] transition-colors"
            onClick={(e) => handlePreviewClick(item, e)}
          >
            <img src={thumbnailUrl} alt={item.filename} className="w-full h-full object-cover" />
          </div>
        )
      }

      if (item.file_type === 'pdf' && thumbnailUrl) {
        return (
          <div
            className="w-10 h-10 rounded border-[2px] border-black bg-white flex items-center justify-center cursor-pointer hover:border-[#FFD93D] transition-colors"
            onClick={(e) => handlePreviewClick(item, e)}
          >
            <FileText className="h-5 w-5 text-red-500" />
          </div>
        )
      }

      if (item.file_type === 'image') {
        return <ImageIcon className="h-5 w-5 text-blue-500" />
      }
      if (item.file_type === 'pdf' || item.file_type === 'text' || item.file_type === 'document') {
        return <FileText className="h-5 w-5 text-red-500" />
      }
      return <File className="h-5 w-5 text-gray-500" />
    }

    const formatDate = (dateString: string): string => {
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)

      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`

      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }

    return (
      <div ref={ref} className={cn("flex flex-col gap-3", className)}>
        {/* Upload Area */}
        <HomeworkUpload onUpload={handleFileUpload} />

        {/* File List */}
        {homeworkList.length > 0 && (
          <div className="border-t-[2px] border-black dark:border-white pt-3">
            <p className="text-[10px] font-black uppercase text-black dark:text-white mb-2">
              Uploaded Files ({homeworkList.length})
            </p>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {homeworkList.map((item) => (
                <div
                  key={item.homework_id}
                  className="flex items-center gap-2 p-2 rounded border-[2px] border-black dark:border-white bg-white dark:bg-black"
                >
                  <div className="shrink-0">
                    {getFileIcon(item)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold truncate text-black dark:text-white">
                      {item.filename}
                    </p>
                    <p className="text-[10px] text-gray-500">
                      {formatDate(item.uploaded_at)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => handleDeleteHomework(item.homework_id, e)}
                    className="h-8 w-8 shrink-0 hover:bg-red-100 hover:text-red-600 border-[2px] border-transparent hover:border-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="p-2 rounded border-[2px] border-red-500 bg-red-50 dark:bg-red-900/20">
            <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Hint Text */}
        <p className="text-[10px] text-gray-500 text-center">
          Upload homework and ask the live tutor for help!
        </p>

        {/* File Preview Dialog */}
        <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
          <DialogContent className="max-w-4xl w-[95vw] h-[90vh] p-0 border-[3px] border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
            <DialogTitle className="sr-only">
              {previewItem?.filename || 'File Preview'}
            </DialogTitle>
            <div className="relative w-full h-full flex flex-col">
              <div className="flex items-center justify-between p-3 border-b-[3px] border-black bg-[#FFD93D]">
                <p className="text-sm font-bold truncate flex-1 pr-4 text-black">
                  {previewItem?.filename}
                </p>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setPreviewOpen(false)}
                  className="h-8 w-8 shrink-0 border-[2px] border-black hover:bg-red-500 hover:text-white rounded-none"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="flex-1 overflow-auto p-4 bg-gray-100">
                {previewItem?.file_type === 'image' && previewUrl && (
                  <div className="flex items-center justify-center h-full">
                    <img
                      src={previewUrl}
                      alt={previewItem.filename}
                      className="max-w-full max-h-full object-contain border-[3px] border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
                    />
                  </div>
                )}
                {previewItem?.file_type === 'pdf' && previewUrl && (
                  <embed
                    src={previewUrl}
                    type="application/pdf"
                    className="w-full h-full border-[3px] border-black"
                  />
                )}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    )
  }
)

HomeworkPanel.displayName = "HomeworkPanel"

export { HomeworkPanel }
