import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// EXTREME NEO-BRUTALISM Badge
const badgeVariants = cva(
  // Base styles - brutal with NO rounded corners
  "inline-flex items-center border-[2px] border-black px-3 py-1 text-xs font-black uppercase tracking-wide transition-all shadow-[2px_2px_0_0_#000] focus:outline-none",
  {
    variants: {
      variant: {
        default:
          "bg-[#FCD34D] text-black hover:shadow-[3px_3px_0_0_#000] hover:translate-x-[-1px] hover:translate-y-[-1px]",
        secondary:
          "bg-white text-black hover:bg-gray-100 hover:shadow-[3px_3px_0_0_#000]",
        destructive:
          "bg-[#FF6B6B] text-black hover:shadow-[3px_3px_0_0_#000]",
        success:
          "bg-[#22C55E] text-black hover:shadow-[3px_3px_0_0_#000]",
        outline:
          "bg-transparent text-black border-[2px] border-black hover:bg-[#FCD34D]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div
      className={cn(badgeVariants({ variant }), className)}
      style={{ borderRadius: 0 }}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
