import { Shield, ShieldAlert, ShieldCheck, ShieldX, HelpCircle, Clock } from "lucide-react";

interface VerificationBadgeProps {
  status?: "unverified" | "checking" | "verified" | "warning" | "failed" | "expired";
}

export function VerificationBadge({ status = "unverified" }: VerificationBadgeProps) {
  let colorClass = "bg-gray-500/15 text-gray-400 border-gray-500/30";
  let label = "Chưa xác thực";
  let Icon = HelpCircle;

  switch (status) {
    case "verified":
      colorClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      label = "Đã xác thực";
      Icon = ShieldCheck;
      break;
    case "checking":
      colorClass = "bg-blue-500/15 text-blue-400 border-blue-500/30 animate-pulse";
      label = "Đang kiểm tra";
      Icon = Shield;
      break;
    case "warning":
      colorClass = "bg-amber-500/15 text-amber-400 border-amber-500/30";
      label = "Cảnh báo";
      Icon = ShieldAlert;
      break;
    case "failed":
      colorClass = "bg-rose-500/15 text-rose-400 border-rose-500/30";
      label = "Thất bại";
      Icon = ShieldX;
      break;
    case "expired":
      colorClass = "bg-amber-700/15 text-amber-500 border-amber-700/30";
      label = "Hết hạn";
      Icon = Clock;
      break;
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${colorClass}`}>
      <Icon className="h-3 w-3" />
      <span>{label}</span>
    </span>
  );
}
