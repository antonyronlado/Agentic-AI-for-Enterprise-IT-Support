import { cn } from "@/lib/utils"

export function Textarea({ className, ...props }) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm transition-colors outline-none placeholder:text-slate-400 focus-visible:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50 resize-none min-h-[100px]",
        className
      )}
      {...props}
    />
  )
}
