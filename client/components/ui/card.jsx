import { cn } from "@/lib/utils"

export function Card({ className, size = "default", ...props }) {
  return (
    <div
      data-slot="card"
      data-size={size}
      className={cn(
        "group/card flex flex-col gap-4 overflow-hidden rounded-xl bg-white py-4 text-sm text-slate-900 ring-1 ring-slate-200 shadow-sm",
        className
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }) {
  return (
    <div
      data-slot="card-header"
      className={cn("grid auto-rows-min items-start gap-1 px-5", className)}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }) {
  return (
    <div
      data-slot="card-title"
      className={cn("text-base font-semibold leading-snug", className)}
      {...props}
    />
  )
}

export function CardDescription({ className, ...props }) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-sm text-slate-500", className)}
      {...props}
    />
  )
}

export function CardAction({ className, ...props }) {
  return (
    <div
      data-slot="card-action"
      className={cn("col-start-2 row-span-2 row-start-1 self-start justify-self-end", className)}
      {...props}
    />
  )
}

export function CardContent({ className, ...props }) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-5", className)}
      {...props}
    />
  )
}

export function CardFooter({ className, ...props }) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center rounded-b-xl border-t border-slate-100 bg-slate-50 p-5", className)}
      {...props}
    />
  )
}
