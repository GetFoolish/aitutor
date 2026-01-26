"use client"

import * as React from "react"
import { Upload, X, FileText, File } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"

interface HomeworkUploadProps {
  onFileSelect?: (file: File) => void
  onUpload?: (file: File) => Promise<void>
  className?: string
}

const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt']
}

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

const HomeworkUpload = React.forwardRef<HTMLDivElement, HomeworkUploadProps>(
  ({ onFileSelect, onUpload, className }, ref) => {
    const [isDragging, setIsDragging] = React.useState(false)
    const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
    const [uploadProgress, setUploadProgress] = React.useState(0)
    const [isUploading, setIsUploading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)
    const fileInputRef = React.useRef<HTMLInputElement>(null)

    const validateFile = (file: File): string | null => {
      const acceptedTypes = Object.keys(ACCEPTED_FILE_TYPES)
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()

      const isValidType = acceptedTypes.some(type =>
        file.type === type ||
        ACCEPTED_FILE_TYPES[type as keyof typeof ACCEPTED_FILE_TYPES].includes(fileExtension)
      )

      if (!isValidType) {
        return 'Unsupported file type. Please upload PDF, JPG, PNG, DOCX, or TXT files.'
      }

      if (file.size > MAX_FILE_SIZE) {
        return 'File size exceeds 10MB limit.'
      }

      return null
    }

    const handleFileChange = async (file: File) => {
      console.log('[HomeworkUpload] handleFileChange called with:', file.name, file.type, file.size)
      const validationError = validateFile(file)

      if (validationError) {
        console.log('[HomeworkUpload] Validation error:', validationError)
        setError(validationError)
        setSelectedFile(null)
        return
      }

      console.log('[HomeworkUpload] File validated, setting selectedFile')
      setError(null)
      setSelectedFile(file)
      onFileSelect?.(file)

      // Auto-upload immediately if onUpload is provided
      if (onUpload) {
        console.log('[HomeworkUpload] Auto-uploading file...')
        setIsUploading(true)
        setUploadProgress(0)

        try {
          const progressInterval = setInterval(() => {
            setUploadProgress(prev => {
              if (prev >= 90) {
                clearInterval(progressInterval)
                return prev
              }
              return prev + 10
            })
          }, 100)

          await onUpload(file)

          clearInterval(progressInterval)
          setUploadProgress(100)

          // Reset after successful upload
          setTimeout(() => {
            setSelectedFile(null)
            setUploadProgress(0)
            setIsUploading(false)
            if (fileInputRef.current) {
              fileInputRef.current.value = ''
            }
          }, 1000)
        } catch (err) {
          let errorMessage = 'Upload failed. Please try again.'
          if (err instanceof Error) {
            errorMessage = err.message
          }
          setError(errorMessage)
          setIsUploading(false)
          setUploadProgress(0)
        }
      }
    }

    const handleDragEnter = (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(true)
    }

    const handleDragLeave = (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)
    }

    const handleDragOver = (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
    }

    const handleDrop = (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const files = e.dataTransfer.files
      if (files && files.length > 0) {
        handleFileChange(files[0])
      }
    }

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        handleFileChange(files[0])
      }
    }

    const handleBrowseClick = () => {
      fileInputRef.current?.click()
    }

    const handleRemoveFile = () => {
      setSelectedFile(null)
      setError(null)
      setUploadProgress(0)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }

    const handleUpload = async () => {
      console.log('[HomeworkUpload] handleUpload called')
      console.log('[HomeworkUpload] selectedFile:', selectedFile?.name)
      console.log('[HomeworkUpload] onUpload defined:', !!onUpload)

      if (!selectedFile || !onUpload) {
        console.log('[HomeworkUpload] Aborting: selectedFile or onUpload missing')
        return
      }

      setIsUploading(true)
      setUploadProgress(0)
      setError(null) // Clear any previous errors

      try {
        // Simulate upload progress
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            if (prev >= 90) {
              clearInterval(progressInterval)
              return prev
            }
            return prev + 10
          })
        }, 100)

        await onUpload(selectedFile)

        clearInterval(progressInterval)
        setUploadProgress(100)

        // Reset after successful upload
        setTimeout(() => {
          setSelectedFile(null)
          setUploadProgress(0)
          setIsUploading(false)
          if (fileInputRef.current) {
            fileInputRef.current.value = ''
          }
        }, 1000)
      } catch (err) {
        // Display user-friendly error message
        let errorMessage = 'Upload failed. Please try again.'

        if (err instanceof Error) {
          errorMessage = err.message
        }

        setError(errorMessage)
        setIsUploading(false)
        setUploadProgress(0)
      }
    }

    const getFileIcon = () => {
      if (!selectedFile) return null

      const extension = selectedFile.name.split('.').pop()?.toLowerCase()

      if (extension === 'pdf' || extension === 'txt' || extension === 'doc' || extension === 'docx') {
        return <FileText className="h-8 w-8 text-muted-foreground" />
      }

      return <File className="h-8 w-8 text-muted-foreground" />
    }

    const formatFileSize = (bytes: number): string => {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    return (
      <div ref={ref} className={cn("space-y-4", className)}>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.txt"
          onChange={handleFileInputChange}
        />

        {/* Fixed-size dropzone - always visible */}
        <div
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "relative flex flex-col items-center justify-center rounded border-[2px] border-dashed p-3 sm:p-4 h-[120px] transition-colors",
            isDragging
              ? "border-[#FFD93D] bg-[#FFD93D]/10"
              : "border-gray-300 hover:border-[#FFD93D]",
            "cursor-pointer"
          )}
          onClick={handleBrowseClick}
        >
          {isUploading ? (
            <div className="w-full space-y-2">
              <div className="w-full h-2 bg-gray-200 rounded overflow-hidden border border-black">
                <div
                  className="h-full bg-[#FFD93D] transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-[10px] text-center text-gray-500 font-medium">
                Uploading... {uploadProgress}%
              </p>
            </div>
          ) : (
            <>
              <Upload className="h-6 w-6 text-gray-400 mb-2" />
              <p className="text-xs font-medium text-center text-gray-600">
                Drop homework or click to browse
              </p>
              <p className="text-[10px] text-gray-400 text-center">
                PDF, JPG, PNG, DOCX, TXT (max 10MB)
              </p>
            </>
          )}
        </div>

        {error && (
          <div className="p-3 sm:p-4 rounded-lg border-[3px] border-destructive bg-destructive/10 shadow-[2px_2px_0_0] shadow-destructive/50">
            <div className="flex items-start gap-2 sm:gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <X className="h-5 w-5 text-destructive" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs sm:text-sm text-destructive font-semibold mb-1">
                  Error
                </p>
                <p className="text-xs sm:text-sm text-destructive break-words">
                  {error}
                </p>
              </div>
              <button
                onClick={() => setError(null)}
                className="flex-shrink-0 text-destructive hover:text-destructive/80 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center -m-2"
                aria-label="Dismiss error"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }
)

HomeworkUpload.displayName = "HomeworkUpload"

export { HomeworkUpload }
