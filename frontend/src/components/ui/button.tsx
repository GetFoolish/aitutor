import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  // Base neo-brutalism button: sharp corners, bold text, hard shadow, minimum 48px height
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none font-bold uppercase tracking-wide border-neo border-black dark:border-white transition-neo focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black dark:focus-visible:ring-white focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:translate-x-1 active:translate-y-1 active:shadow-none [&_svg]:pointer-events-none [&_svg]:size-5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-neo-yellow text-black shadow-neo hover:bg-[#FFE066] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-neo-sm dark:shadow-neo-dark dark:hover:shadow-neo-sm",
        destructive:
          "bg-neo-red text-white shadow-neo hover:bg-[#FF8787] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-neo-sm",
        outline:
          "border-neo border-black dark:border-white bg-white dark:bg-black text-black dark:text-white shadow-neo hover:bg-gray-50 dark:hover:bg-gray-900 hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-neo-sm",
        secondary:
          "bg-neo-violet text-black shadow-neo hover:bg-[#D4C5FD] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-neo-sm",
        ghost: "border-none shadow-none hover:bg-gray-100 dark:hover:bg-gray-800",
        link: "text-black dark:text-white underline-offset-4 hover:underline border-none shadow-none lowercase",
      },
      size: {
        default: "h-12 px-6 py-3 text-base",
        sm: "h-10 px-4 py-2 text-sm",
        lg: "h-14 px-8 py-4 text-lg",
        xl: "h-16 px-10 py-5 text-xl",
        icon: "h-12 w-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
