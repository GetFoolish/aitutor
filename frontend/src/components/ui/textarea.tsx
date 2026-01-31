import * as React from "react"

import { cn } from "@/lib/utils"

// EXTREME NEO-BRUTALISM Textarea Component
const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        // Base styles - EXTREME NEO-BRUTALISM
        "flex min-h-[120px] w-full bg-white px-4 py-3 text-base font-bold font-mono text-black resize-y",
        // Border - thick black, NO rounded corners
        "border-[3px] border-black",
        // Shadow - brutal offset
        "shadow-[4px_4px_0_0_#000]",
        // Focus - yellow highlight, larger shadow
        "focus:bg-[#FCD34D] focus:shadow-[6px_6px_0_0_#000] focus:outline-none",
        // Hover
        "hover:shadow-[5px_5px_0_0_#000]",
        // Placeholder
        "placeholder:text-black placeholder:opacity-50 placeholder:font-bold",
        // Disabled
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-gray-100",
        // Transition
        "transition-all duration-100",
        className
      )}
      style={{ borderRadius: 0 }}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }
