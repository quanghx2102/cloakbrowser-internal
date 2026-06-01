import { Lock, Unlock } from "lucide-react";

interface IdentityLockBadgeProps {
  locked: boolean;
}

export function IdentityLockBadge({ locked }: IdentityLockBadgeProps) {
  if (locked) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 font-semibold backdrop-blur-sm shadow-sm transition-all hover:bg-rose-500/20">
        <Lock className="h-3 w-3 flex-shrink-0 animate-pulse text-rose-400" />
        <span>Locked</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold backdrop-blur-sm shadow-sm transition-all hover:bg-emerald-500/20">
      <Unlock className="h-3 w-3 flex-shrink-0 text-emerald-400" />
      <span>Unlocked</span>
    </span>
  );
}
