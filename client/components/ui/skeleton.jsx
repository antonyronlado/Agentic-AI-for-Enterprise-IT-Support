import { cn } from "@/lib/utils"

export function Skeleton({ className, ...props }) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-slate-200/50 animate-pulse rounded-md", className)}
      {...props}
    />
  )
}
