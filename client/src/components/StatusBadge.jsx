import { Loader2, CheckCircle2, AlertTriangle, Clock, XCircle, Zap } from 'lucide-react';
import { motion } from 'motion/react';

const CONFIG = {
  open: {
    label: 'Open',
    dot: 'bg-blue-500',
    badge: 'bg-blue-50 text-blue-700 border-blue-200',
    icon: null,
    animated: false,
  },
  in_progress: {
    label: 'In Progress',
    dot: 'bg-amber-500',
    badge: 'bg-amber-50 text-amber-700 border-amber-200',
    icon: Loader2,
    animated: true,
  },
  analyzing: {
    label: 'Analyzing',
    dot: 'bg-violet-500',
    badge: 'bg-violet-50 text-violet-700 border-violet-200',
    icon: Loader2,
    animated: true,
  },
  risk_assessment: {
    label: 'Risk Check',
    dot: 'bg-orange-500',
    badge: 'bg-orange-50 text-orange-700 border-orange-200',
    icon: Loader2,
    animated: true,
  },
  resolving: {
    label: 'Resolving',
    dot: 'bg-amber-500',
    badge: 'bg-amber-50 text-amber-700 border-amber-200',
    icon: Loader2,
    animated: true,
  },
  resolved: {
    label: 'Resolved',
    dot: 'bg-emerald-500',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    icon: CheckCircle2,
    animated: false,
  },
  escalated: {
    label: 'Escalated',
    dot: 'bg-red-500',
    badge: 'bg-red-50 text-red-700 border-red-200',
    icon: AlertTriangle,
    animated: false,
  },
  failed: {
    label: 'Failed',
    dot: 'bg-rose-600',
    badge: 'bg-rose-50 text-rose-700 border-rose-300',
    icon: XCircle,
    animated: false,
  },
};

const sizeClasses = {
  sm: 'text-[9px] px-1.5 py-0.5 gap-1',
  md: 'text-[10px] px-2 py-0.5 gap-1.5',
  lg: 'text-xs px-2.5 py-1 gap-1.5',
};

const iconSizes = {
  sm: 'w-2.5 h-2.5',
  md: 'w-3 h-3',
  lg: 'w-3.5 h-3.5',
};

const dotSizes = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

/**
 * Unified status badge used across both dashboards.
 * @param {string} status - ticket status key
 * @param {'sm'|'md'|'lg'} size
 * @param {boolean} showDot - show left-side color dot instead of icon (default false)
 * @param {boolean} pill - pill shape (default true)
 */
export function StatusBadge({ status, size = 'md', showDot = false, pill = true }) {
  const cfg = CONFIG[status] || CONFIG.open;
  const Icon = cfg.icon;
  const shapeClass = pill ? 'rounded-full' : 'rounded-md';

  return (
    <span
      className={`
        inline-flex items-center font-mono font-medium uppercase tracking-wide border
        ${shapeClass} ${sizeClasses[size]} ${cfg.badge}
      `}
    >
      {showDot ? (
        <span className={`rounded-full shrink-0 ${dotSizes[size]} ${cfg.dot}`} />
      ) : Icon ? (
        <Icon
          className={`shrink-0 ${iconSizes[size]} ${cfg.animated ? 'animate-spin' : ''}`}
        />
      ) : null}
      {cfg.label}
    </span>
  );
}

/**
 * Standalone animated dot (for timeline left rail).
 */
export function StatusDot({ status, size = 'md' }) {
  const cfg = CONFIG[status] || CONFIG.open;
  const isAnimated = cfg.animated;

  const dotSize = {
    sm: 'w-2 h-2',
    md: 'w-2.5 h-2.5',
    lg: 'w-3 h-3',
  }[size];

  return (
    <span className="relative flex items-center justify-center">
      {isAnimated && (
        <span
          className={`absolute rounded-full opacity-40 animate-ping ${dotSize} ${cfg.dot}`}
        />
      )}
      <span className={`relative rounded-full ${dotSize} ${cfg.dot}`} />
    </span>
  );
}

/**
 * AI action label shown in the timeline.
 */
export function AIActionLabel({ status, automated }) {
  if (status === 'resolved' && automated) {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider text-emerald-600">
        <Zap className="w-2.5 h-2.5" />
        Auto-resolved by AI
      </span>
    );
  }
  if (status === 'resolved') {
    return (
      <span className="text-[9px] font-mono uppercase tracking-wider text-emerald-600">
        Resolved by agent
      </span>
    );
  }
  if (status === 'escalated') {
    return (
      <span className="text-[9px] font-mono uppercase tracking-wider text-red-600">
        Escalated — agent review
      </span>
    );
  }
  if (['analyzing', 'risk_assessment', 'resolving', 'in_progress'].includes(status)) {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider text-violet-600">
        <motion.span
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ repeat: Infinity, duration: 1.4, ease: 'easeInOut' }}
        >
          ●
        </motion.span>
        AI processing
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="text-[9px] font-mono uppercase tracking-wider text-rose-600">
        Pipeline failed — needs attention
      </span>
    );
  }
  return (
    <span className="text-[9px] font-mono uppercase tracking-wider text-slate-400">
      Awaiting AI triage
    </span>
  );
}
