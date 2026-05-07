import { cn } from "@/lib/cn";

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block w-4 h-4 rounded-full border-2 border-white/20 border-t-cyan-400 animate-spin",
        className
      )}
    />
  );
}
