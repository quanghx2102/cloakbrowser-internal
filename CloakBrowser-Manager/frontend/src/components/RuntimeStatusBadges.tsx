import {
  Globe,
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Lock,
  Unlock,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from "lucide-react";

interface RuntimeStatusBadgesProps {
  proxyStatus?: string;
  verificationStatus?: string;
  runtimeGuardianStatus?: string;
  fingerprintLocked: boolean;
  lastCheck?: string | null;
}

export function RuntimeStatusBadges({
  proxyStatus,
  verificationStatus = "unverified",
  runtimeGuardianStatus = "idle",
  fingerprintLocked,
  lastCheck,
}: RuntimeStatusBadgesProps) {
  // 1. Proxy Status Badge
  const renderProxyBadge = () => {
    let colorClass = "bg-gray-500/10 border-gray-500/20 text-gray-400";
    let label = "No Proxy";
    let Icon = Globe;

    if (proxyStatus) {
      switch (proxyStatus) {
        case "PROXY_OK":
          colorClass = "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 font-semibold";
          label = "Proxy: Connected";
          break;
        case "PROXY_TIMEOUT":
          colorClass = "bg-amber-500/10 border-amber-500/20 text-amber-400 font-semibold";
          label = "Proxy: Timeout";
          Icon = AlertTriangle;
          break;
        case "PROXY_CONNECTION_FAILED":
          colorClass = "bg-rose-500/10 border-rose-500/20 text-rose-400 font-semibold";
          label = "Proxy: Connect Failed";
          Icon = XCircle;
          break;
        case "PROXY_AUTH_FAILED":
          colorClass = "bg-rose-500/10 border-rose-500/20 text-rose-400 font-semibold animate-pulse";
          label = "Proxy: Auth Failed";
          Icon = ShieldX;
          break;
        default:
          colorClass = "bg-rose-500/10 border-rose-500/20 text-rose-400 font-semibold";
          label = `Proxy: ${proxyStatus}`;
          Icon = XCircle;
      }
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] border backdrop-blur-sm shadow-sm ${colorClass}`}>
        <Icon className="h-2.5 w-2.5" />
        <span>{label}</span>
      </span>
    );
  };

  // 2. Verification Badge
  const renderVerificationBadge = () => {
    let colorClass = "bg-gray-500/10 border-gray-500/20 text-gray-400";
    let label = "Chưa xác thực";
    let Icon = HelpCircle;

    switch (verificationStatus) {
      case "verified":
        colorClass = "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 font-semibold";
        label = "Verified";
        Icon = ShieldCheck;
        break;
      case "checking":
        colorClass = "bg-blue-500/10 border-blue-500/20 text-blue-400 font-semibold animate-pulse";
        label = "Verifying...";
        Icon = Shield;
        break;
      case "warning":
        colorClass = "bg-amber-500/10 border-amber-500/20 text-amber-400 font-semibold";
        label = "Verify Warning";
        Icon = ShieldAlert;
        break;
      case "failed":
        colorClass = "bg-rose-500/10 border-rose-500/20 text-rose-400 font-semibold";
        label = "Verify Failed";
        Icon = ShieldX;
        break;
      case "expired":
        colorClass = "bg-amber-700/10 border-amber-700/20 text-amber-500 font-semibold";
        label = "Verify Expired";
        Icon = Clock;
        break;
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] border backdrop-blur-sm shadow-sm ${colorClass}`}>
        <Icon className="h-2.5 w-2.5" />
        <span>{label}</span>
      </span>
    );
  };

  // 3. Guardian Badge
  const renderGuardianBadge = () => {
    let colorClass = "bg-gray-500/10 border-gray-500/20 text-gray-400";
    let label = "Guardian: Idle";
    let Icon = Activity;

    switch (runtimeGuardianStatus) {
      case "monitoring":
        colorClass = "bg-blue-500/10 border-blue-500/20 text-blue-400 font-semibold animate-pulse";
        label = "Guardian: Monitoring";
        break;
      case "healthy":
        colorClass = "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 font-semibold";
        label = "Guardian: Healthy";
        Icon = CheckCircle2;
        break;
      case "warning":
        colorClass = "bg-amber-500/10 border-amber-500/20 text-amber-400 font-semibold";
        label = "Guardian: Warning";
        Icon = AlertTriangle;
        break;
      case "critical":
        colorClass = "bg-rose-500/10 border-rose-500/20 text-rose-400 font-semibold animate-bounce";
        label = "Guardian: CRITICAL";
        Icon = XCircle;
        break;
      case "stopped_by_guardian":
        colorClass = "bg-rose-600/10 border-rose-600/20 text-rose-500 font-bold";
        label = "STOPPED BY GUARDIAN";
        Icon = XCircle;
        break;
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] border backdrop-blur-sm shadow-sm ${colorClass}`}>
        <Icon className="h-2.5 w-2.5" />
        <span>{label}</span>
      </span>
    );
  };

  // 4. Fingerprint Lock Badge
  const renderFingerprintBadge = () => {
    if (fingerprintLocked) {
      return (
        <span className="inline-flex items-center gap-1.5 text-[9px] px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 font-semibold backdrop-blur-sm shadow-sm">
          <Lock className="h-2.5 w-2.5" />
          <span>Locked</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold backdrop-blur-sm shadow-sm">
        <Unlock className="h-2.5 w-2.5" />
        <span>Unlocked</span>
      </span>
    );
  };

  // 5. Last Check Badge
  const renderLastCheckBadge = () => {
    if (!lastCheck) return null;
    let timeStr = "";
    try {
      const date = new Date(lastCheck);
      timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      timeStr = lastCheck;
    }

    return (
      <span className="inline-flex items-center gap-1.5 text-[9px] px-2 py-0.5 rounded-full bg-gray-500/10 border border-gray-500/20 text-gray-500 backdrop-blur-sm">
        <Clock className="h-2.5 w-2.5" />
        <span>Check: {timeStr}</span>
      </span>
    );
  };

  return (
    <div className="flex flex-wrap gap-1.5 mt-1 items-center">
      {renderProxyBadge()}
      {renderVerificationBadge()}
      {renderGuardianBadge()}
      {renderFingerprintBadge()}
      {renderLastCheckBadge()}
    </div>
  );
}
