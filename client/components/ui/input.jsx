import { Input as InputPrimitive } from "@base-ui/react/input"
import { cn } from "@/lib/utils"

export function Input({ className, type, ...props }) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "h-10 w-full min-w-0 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm transition-colors outline-none placeholder:text-white/30 focus-visible:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/20 disabled:pointer-events-none disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}
