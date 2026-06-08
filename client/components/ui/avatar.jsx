import { cn } from "@/lib/utils"

export function Avatar({ className, ...props }) {
  return (
    <span
      data-slot="avatar"
      className={cn(
        "relative flex size-8 shrink-0 overflow-hidden rounded-full",
        className
      )}
      {...props}
    />
  )
}

export function AvatarImage({ className, src, alt, ...props }) {
  return (
    <img
      data-slot="avatar-image"
      src={src}
      alt={alt}
      className={cn("aspect-square size-full object-cover", className)}
      {...props}
    />
  )
}

export function AvatarFallback({ className, ...props }) {
  return (
    <span
      data-slot="avatar-fallback"
      className={cn(
        "flex size-full items-center justify-center rounded-full bg-slate-100 text-xs font-medium uppercase text-slate-600",
        className
      )}
      {...props}
    />
  )
}
