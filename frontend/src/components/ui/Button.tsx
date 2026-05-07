import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost" | "outline" | "subtle";

export function Button({
  children, variant = "primary", className, ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode; variant?: Variant }) {
  const styles: Record<Variant, string> = {
    primary:
      "bg-gradient-to-r from-violet-600 to-cyan-500 text-white hover:opacity-90 shadow-[0_0_20px_-6px_rgba(124,58,237,0.6)]",
    ghost: "text-zinc-300 hover:text-white hover:bg-white/5",
    outline: "border border-white/10 text-zinc-200 hover:bg-white/5",
    subtle: "bg-white/5 text-zinc-200 hover:bg-white/10",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        styles[variant],
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
