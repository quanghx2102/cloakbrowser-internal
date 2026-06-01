interface StatusIndicatorProps {
  status: "running" | "stopped" | "launching";
  size?: "sm" | "md";
  showLabel?: boolean;
}

export function StatusIndicator({ status, size = "sm", showLabel = false }: StatusIndicatorProps) {
  const sizeClass = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";

  const dotColor =
    status === "running"
      ? "bg-emerald-400"
      : status === "launching"
        ? "bg-yellow-400"
        : "bg-gray-500";

  const labelText =
    status === "running" ? "Đang chạy" : status === "launching" ? "Đang khởi chạy" : "Đã dừng";

  const labelColor =
    status === "running"
      ? "text-emerald-400"
      : status === "launching"
        ? "text-yellow-400"
        : "text-gray-500";

  return (
    <span className={`inline-flex items-center gap-1.5 ${showLabel ? "" : ""}`}>
      <span className="relative inline-flex">
        {(status === "running" || status === "launching") && (
          <span
            className={`absolute inline-flex ${sizeClass} rounded-full ${dotColor} opacity-75 animate-ping`}
          />
        )}
        <span
          className={`relative inline-flex ${sizeClass} rounded-full ${dotColor}`}
        />
      </span>
      {showLabel && (
        <span className={`text-xs font-medium ${labelColor}`}>{labelText}</span>
      )}
    </span>
  );
}
