"use client"

import * as React from "react"
import { Send, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { homeworkService, type ConversationTurn } from "@/services/homework-service"

interface HomeworkChatProps {
  homeworkId: string
  className?: string
}

export const HomeworkChat = React.forwardRef<HTMLDivElement, HomeworkChatProps>(
  ({ homeworkId, className }, ref) => {
    const [messages, setMessages] = React.useState<ConversationTurn[]>([])
    const [inputValue, setInputValue] = React.useState("")
    const [isLoading, setIsLoading] = React.useState(false)
    const [isLoadingHistory, setIsLoadingHistory] = React.useState(true)
    const [error, setError] = React.useState<string | null>(null)
    const scrollAreaRef = React.useRef<HTMLDivElement>(null)
    const textareaRef = React.useRef<HTMLTextAreaElement>(null)

    // Load conversation history when homeworkId changes
    React.useEffect(() => {
      loadConversationHistory()
    }, [homeworkId])

    // Auto-scroll to bottom when messages change
    React.useEffect(() => {
      if (scrollAreaRef.current) {
        const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
        if (scrollContainer) {
          scrollContainer.scrollTop = scrollContainer.scrollHeight
        }
      }
    }, [messages])

    const loadConversationHistory = async () => {
      setIsLoadingHistory(true)
      setError(null)
      try {
        const homework = await homeworkService.getHomework(homeworkId)
        setMessages(homework.conversation_history || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversation history')
      } finally {
        setIsLoadingHistory(false)
      }
    }

    const handleSendMessage = async () => {
      const question = inputValue.trim()
      if (!question || isLoading) return

      // Add user message to UI immediately
      const userMessage: ConversationTurn = {
        role: 'user',
        content: question,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, userMessage])
      setInputValue("")
      setIsLoading(true)
      setError(null)

      try {
        // Call API for AI response
        const response = await homeworkService.askQuestion(homeworkId, question)

        // Add AI response to messages
        const aiMessage: ConversationTurn = {
          role: 'assistant',
          content: response.response,
          timestamp: response.timestamp,
        }
        setMessages(prev => [...prev, aiMessage])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to get AI response')
        // Remove the user message if AI failed
        setMessages(prev => prev.slice(0, -1))
        // Restore input value
        setInputValue(question)
      } finally {
        setIsLoading(false)
        // Focus back on textarea
        textareaRef.current?.focus()
      }
    }

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSendMessage()
      }
    }

    const formatTime = (timestamp: string): string => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      })
    }

    return (
      <div ref={ref} className={cn("h-full flex flex-col", className)}>
        {/* Messages Area */}
        <ScrollArea ref={scrollAreaRef} className="flex-1 px-3 pb-3">
          {isLoadingHistory ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <p className="text-sm font-medium">Loading conversation...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="p-4 sm:p-5 rounded-lg border-[3px] border-border bg-background/50 max-w-sm w-full">
                <p className="text-sm sm:text-base font-bold text-foreground mb-2">Ask me anything!</p>
                <p className="text-xs sm:text-sm text-muted-foreground mb-3">
                  I'm here to help you with your homework. Try asking:
                </p>
                <div className="space-y-1.5 text-left">
                  <p className="text-xs sm:text-sm text-muted-foreground px-2 sm:px-3 py-1.5 sm:py-2 rounded bg-background border-[2px] border-border">
                    "Can you explain problem 1?"
                  </p>
                  <p className="text-xs sm:text-sm text-muted-foreground px-2 sm:px-3 py-1.5 sm:py-2 rounded bg-background border-[2px] border-border">
                    "What's the main concept here?"
                  </p>
                  <p className="text-xs sm:text-sm text-muted-foreground px-2 sm:px-3 py-1.5 sm:py-2 rounded bg-background border-[2px] border-border">
                    "How do I get started?"
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-2 sm:space-y-3 py-2">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={cn(
                    "flex",
                    message.role === 'user' ? "justify-end" : "justify-start"
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[90%] sm:max-w-[85%] p-2.5 sm:p-3 rounded-lg border-[3px] shadow-[2px_2px_0_0_rgba(0,0,0,0.8)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.2)]",
                      message.role === 'user'
                        ? "bg-[#4ADE80] border-black dark:border-white text-black"
                        : "bg-[#FFD93D] border-black dark:border-white text-black"
                    )}
                  >
                    <div className="whitespace-pre-wrap text-sm sm:text-base font-medium break-words leading-relaxed">
                      {message.content}
                    </div>
                    <div className={cn(
                      "text-[10px] sm:text-xs mt-1.5 font-bold",
                      message.role === 'user' ? "text-black/60" : "text-black/60"
                    )}>
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[90%] sm:max-w-[85%] p-2.5 sm:p-3 rounded-lg border-[3px] border-black dark:border-white bg-[#FFD93D] shadow-[2px_2px_0_0_rgba(0,0,0,0.8)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.2)]">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-black animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 rounded-full bg-black animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 rounded-full bg-black animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <p className="text-xs sm:text-sm font-bold text-black/70">AI is thinking...</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Error Display */}
        {error && (
          <div className="px-3 pb-2">
            <div className="p-2 sm:p-3 rounded-lg border-[2px] border-destructive bg-destructive/10">
              <p className="text-xs sm:text-sm text-destructive font-medium break-words">{error}</p>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t-[3px] border-border bg-background p-2 sm:p-3">
          <div className="flex gap-2">
            <Textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your homework..."
              disabled={isLoading}
              className="min-h-[52px] sm:min-h-[60px] max-h-[120px] resize-none border-[3px] border-border focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-primary font-medium text-sm sm:text-base"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              size="icon"
              className="h-[52px] w-[52px] sm:h-[60px] sm:w-[60px] min-w-[48px] min-h-[48px] shrink-0 border-[3px] border-black dark:border-white bg-[#ADFF2F] hover:bg-[#ADFF2F]/90 text-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.2)] transition-all disabled:opacity-50 disabled:shadow-[2px_2px_0_0_rgba(0,0,0,0.5)]"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 sm:h-6 sm:w-6 animate-spin" />
              ) : (
                <Send className="h-5 w-5 sm:h-6 sm:w-6" />
              )}
            </Button>
          </div>
          <p className="text-[10px] sm:text-xs text-muted-foreground mt-1.5 sm:mt-2 font-medium">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    )
  }
)

HomeworkChat.displayName = "HomeworkChat"
