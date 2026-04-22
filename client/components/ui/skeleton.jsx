import { cn } from "@/lib/utils"

export function Skeleton({ className, ...props }) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-white/5 animate-pulse rounded-md", className)}
      {...props}
    />
  )
}
