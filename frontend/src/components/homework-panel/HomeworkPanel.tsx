"use client"

import * as React from "react"
import { Upload, BookOpen, MessageSquare, FileText, Image as ImageIcon, File, Trash2, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { HomeworkUpload } from "./HomeworkUpload"
import { HomeworkChat } from "./HomeworkChat"
import { homeworkService, type HomeworkItem } from "@/services/homework-service"

interface HomeworkPanelProps {
  className?: string
  onTabChange?: (tab: string) => void
}

const HomeworkPanel = React.forwardRef<HTMLDivElement, HomeworkPanelProps>(
  ({ className, onTabChange }, ref) => {
    const [homeworkList, setHomeworkList] = React.useState<HomeworkItem[]>([])
    const [isLoading, setIsLoading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)
    const [selectedTab, setSelectedTab] = React.useState("list")
    const [selectedHomework, setSelectedHomework] = React.useState<string | null>(null)
    const [previewOpen, setPreviewOpen] = React.useState(false)
    const [previewItem, setPreviewItem] = React.useState<HomeworkItem | null>(null)
    const [previewUrl, setPreviewUrl] = React.useState<string | null>(null)
    const [thumbnailUrls, setThumbnailUrls] = React.useState<Record<string, string>>({})

    // Fetch homework list on mount and when tab changes to "list"
    React.useEffect(() => {
      if (selectedTab === "list") {
        fetchHomeworkList()
      }
    }, [selectedTab])

    // Load thumbnails for images and PDFs
    React.useEffect(() => {
      const loadThumbnails = async () => {
        const urls: Record<string, string> = {}

        for (const item of homeworkList) {
          // Only load thumbnails for images and PDFs
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

      // Cleanup object URLs on unmount or when homework list changes
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
      e.stopPropagation() // Prevent homework item click

      // Only allow preview for images and PDFs
      if (item.file_type !== 'image' && item.file_type !== 'pdf') {
        return
      }

      try {
        // Reuse thumbnail URL if available, otherwise fetch
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
        await homeworkService.uploadHomework(file)
        // Refresh the homework list after successful upload
        await fetchHomeworkList()
        // Switch to "list" tab to show the uploaded homework
        setSelectedTab("list")
      } catch (err) {
        throw err // Let HomeworkUpload handle the error
      }
    }

    const handleDeleteHomework = async (homeworkId: string, e: React.MouseEvent) => {
      e.stopPropagation() // Prevent item click

      if (!confirm('Are you sure you want to delete this homework?')) {
        return
      }

      try {
        await homeworkService.deleteHomework(homeworkId)
        // Refresh the list after deletion
        await fetchHomeworkList()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete homework')
      }
    }

    const handleHomeworkClick = (homeworkId: string) => {
      setSelectedHomework(homeworkId)
      setSelectedTab("chat")
    }

    const getFilePreviewOrIcon = (item: HomeworkItem) => {
      const thumbnailUrl = thumbnailUrls[item.homework_id]

      // Show thumbnail for images
      if (item.file_type === 'image' && thumbnailUrl) {
        return (
          <div
            className="w-16 h-16 rounded-lg border-[3px] border-border overflow-hidden cursor-pointer hover:border-primary transition-colors"
            onClick={(e) => handlePreviewClick(item, e)}
          >
            <img
              src={thumbnailUrl}
              alt={item.filename}
              className="w-full h-full object-cover"
            />
          </div>
        )
      }

      // Show first page preview for PDFs
      if (item.file_type === 'pdf' && thumbnailUrl) {
        return (
          <div
            className="w-16 h-16 rounded-lg border-[3px] border-border bg-muted flex items-center justify-center cursor-pointer hover:border-primary transition-colors overflow-hidden"
            onClick={(e) => handlePreviewClick(item, e)}
          >
            <embed
              src={thumbnailUrl}
              type="application/pdf"
              className="w-full h-full pointer-events-none"
            />
          </div>
        )
      }

      // Fallback to icons for other file types
      if (item.file_type === 'image') {
        return <ImageIcon className="h-8 w-8 text-muted-foreground" />
      }
      if (item.file_type === 'pdf' || item.file_type === 'text' || item.file_type === 'document') {
        return <FileText className="h-8 w-8 text-muted-foreground" />
      }
      return <File className="h-8 w-8 text-muted-foreground" />
    }

    const formatDate = (dateString: string): string => {
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`

      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }

    const formatFileSize = (bytes: number): string => {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const handleTabChange = (value: string) => {
      setSelectedTab(value)
      onTabChange?.(value)
    }

    return (
      <div ref={ref} className={cn("h-full flex flex-col", className)}>
        <Tabs value={selectedTab} onValueChange={handleTabChange} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3 border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] p-1 rounded-none">
            <TabsTrigger
              value="upload"
              className="data-[state=active]:bg-[#FFD93D] data-[state=active]:text-black text-black dark:text-white border-[2px] border-transparent data-[state=active]:border-black dark:data-[state=active]:border-white font-black text-xs uppercase rounded-none shadow-none data-[state=active]:shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
            >
              <Upload className="h-3.5 w-3.5 mr-1.5" />
              Upload
            </TabsTrigger>
            <TabsTrigger
              value="list"
              className="data-[state=active]:bg-[#C4B5FD] data-[state=active]:text-black text-black dark:text-white border-[2px] border-transparent data-[state=active]:border-black dark:data-[state=active]:border-white font-black text-xs uppercase rounded-none shadow-none data-[state=active]:shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
            >
              <BookOpen className="h-3.5 w-3.5 mr-1.5" />
              My Homework
            </TabsTrigger>
            <TabsTrigger
              value="chat"
              className="data-[state=active]:bg-[#ADFF2F] data-[state=active]:text-black text-black dark:text-white border-[2px] border-transparent data-[state=active]:border-black dark:data-[state=active]:border-white font-black text-xs uppercase rounded-none shadow-none data-[state=active]:shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
              disabled={!selectedHomework}
            >
              <MessageSquare className="h-3.5 w-3.5 mr-1.5" />
              Chat
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="flex-1 mt-3 px-1">
            <HomeworkUpload onUpload={handleFileUpload} />
          </TabsContent>

          <TabsContent value="list" className="flex-1 mt-3 overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-muted-foreground font-medium">Loading homework...</p>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full p-4">
                <div className="p-3 rounded-lg border-[3px] border-destructive bg-destructive/10">
                  <p className="text-sm text-destructive font-medium">{error}</p>
                </div>
              </div>
            ) : homeworkList.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <BookOpen className="h-12 w-12 text-muted-foreground mb-3" />
                <p className="text-sm font-bold text-foreground mb-1">No homework yet</p>
                <p className="text-xs text-muted-foreground">
                  Upload your first assignment to get started!
                </p>
              </div>
            ) : (
              <div className="h-full overflow-y-auto pr-2 space-y-2">
                {homeworkList.map((item) => (
                  <div
                    key={item.homework_id}
                    onClick={() => handleHomeworkClick(item.homework_id)}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg border-[3px] border-border bg-background cursor-pointer transition-all hover:border-primary hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]",
                      selectedHomework === item.homework_id && "border-primary bg-primary/5"
                    )}
                  >
                    <div className="shrink-0">
                      {getFilePreviewOrIcon(item)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold truncate text-foreground">
                        {item.filename}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <p className="text-xs text-muted-foreground">
                          {formatDate(item.uploaded_at)}
                        </p>
                        <span className="text-xs text-muted-foreground">•</span>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(item.file_size)}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleDeleteHomework(item.homework_id, e)}
                      className="h-8 w-8 shrink-0 hover:bg-destructive hover:text-destructive-foreground border-[2px] border-transparent hover:border-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="chat" className="flex-1 mt-3 overflow-hidden">
            {selectedHomework ? (
              <HomeworkChat homeworkId={selectedHomework} className="h-full" />
            ) : (
              <div className="flex items-center justify-center h-full text-center px-4">
                <p className="text-sm text-muted-foreground">
                  Select a homework item to start chatting
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* File Preview Dialog */}
        <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
          <DialogContent className="max-w-4xl w-[90vw] h-[90vh] p-0 border-[3px] border-black dark:border-white rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.5)]">
            <DialogTitle className="sr-only">
              {previewItem?.filename || 'File Preview'}
            </DialogTitle>
            <div className="relative w-full h-full flex flex-col">
              {/* Header with filename and close button */}
              <div className="flex items-center justify-between p-4 border-b-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
                <p className="text-sm font-bold truncate flex-1 pr-4 text-foreground">
                  {previewItem?.filename}
                </p>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setPreviewOpen(false)}
                  className="h-8 w-8 shrink-0 border-[2px] border-black dark:border-white hover:bg-destructive hover:text-destructive-foreground hover:border-destructive rounded-none"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {/* Preview content */}
              <div className="flex-1 overflow-auto p-4 bg-muted/30">
                {previewItem?.file_type === 'image' && previewUrl && (
                  <div className="flex items-center justify-center h-full">
                    <img
                      src={previewUrl}
                      alt={previewItem.filename}
                      className="max-w-full max-h-full object-contain rounded-lg border-[3px] border-border shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
                    />
                  </div>
                )}
                {previewItem?.file_type === 'pdf' && previewUrl && (
                  <embed
                    src={previewUrl}
                    type="application/pdf"
                    className="w-full h-full rounded-lg border-[3px] border-border shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
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
