import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

// EXTREME NEO-BRUTALISM TabsList
const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      // Base styles - brutal
      "inline-flex h-12 items-center justify-center p-0 bg-white",
      // Border - thick black
      "border-[3px] border-black",
      // Shadow
      "shadow-[4px_4px_0_0_#000]",
      className
    )}
    style={{ borderRadius: 0 }}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

// EXTREME NEO-BRUTALISM TabsTrigger
const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      // Base styles - brutal
      "inline-flex items-center justify-center whitespace-nowrap px-6 py-3 text-sm font-black uppercase tracking-wide text-black",
      // Border
      "border-r-[3px] border-black last:border-r-0",
      // Transitions
      "transition-all duration-100",
      // Inactive state
      "bg-white",
      // Active state - yellow highlight
      "data-[state=active]:bg-[#FCD34D] data-[state=active]:text-black",
      // Hover
      "hover:bg-[#FCD34D]/50",
      // Focus
      "focus-visible:outline-none focus-visible:bg-[#FCD34D]",
      // Disabled
      "disabled:pointer-events-none disabled:opacity-50",
      className
    )}
    style={{ borderRadius: 0 }}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

// EXTREME NEO-BRUTALISM TabsContent
const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-4 focus-visible:outline-none",
      className
    )}
    style={{ borderRadius: 0 }}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
