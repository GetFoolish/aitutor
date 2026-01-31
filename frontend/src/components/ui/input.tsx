import * as React from "react"

import { cn } from "@/lib/utils"

// EXTREME NEO-BRUTALISM Input Component
const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Base styles - EXTREME NEO-BRUTALISM
          "flex h-12 w-full bg-white px-4 py-3 text-base font-bold font-mono text-black",
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
          // File input
          "file:border-0 file:bg-black file:text-white file:font-bold file:mr-4 file:px-4 file:py-2",
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
  }
)
Input.displayName = "Input"

export { Input }
