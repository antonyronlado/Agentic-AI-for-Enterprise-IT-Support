/**
 * TicketCard — slim queue item for the Admin sidebar.
 * (The employee-facing timeline uses TicketTimeline.jsx instead.)
 */
import { motion } from 'motion/react';
import { StatusBadge, StatusDot } from './StatusBadge';
import { Clock, ShieldAlert, AlertOctagon, Zap } from 'lucide-react';

const priorityDot = {
  low:      'bg-slate-400',
  medium:   'bg-blue-500',
  high:     'bg-amber-500',
  critical: 'bg-red-500',
};

function formatAge(ts) {
  const d = Math.floor((Date.now() - ts) / 60000);
  if (d < 60)   return `${d}m`;
  if (d < 1440) return `${Math.floor(d / 60)}h`;
  return `${Math.floor(d / 1440)}d`;
}

export function TicketCard({ ticket, role = 'user', onClick, isSelected }) {
  const statusKey = ticket.status || 'open';
  const isAdmin   = role === 'admin';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.22 }}
      onClick={onClick}
      className={`
        group relative cursor-pointer rounded-xl border p-3 transition-all duration-150
        ${isSelected
          ? 'bg-indigo-50/80 border-indigo-200 shadow-[0_0_0_1px_rgba(91,95,207,0.15)]'
          : 'bg-white border-slate-200/80 hover:border-primary/25 hover:bg-slate-50/80'}
      `}
    >
      {/* Selected left accent bar */}
      {isSelected && (
        <motion.div
          layoutId="selected-bar"
          className="absolute left-0 top-2 bottom-2 w-0.5 rounded-r-full bg-primary"
        />
      )}

      <div className="flex items-start gap-2.5 pl-1">
        {/* Status dot */}
        <div className="pt-0.5 shrink-0">
          <StatusDot status={statusKey} size="sm" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-1.5">
          {/* Top row: badges */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <StatusBadge status={statusKey} size="sm" />

            {isAdmin && ticket.risk_level && ticket.risk_level !== 'low' && (
              <span className={`inline-flex items-center gap-0.5 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-full border ${
                ticket.risk_level === 'high'
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                <ShieldAlert className="w-2.5 h-2.5" />
                {ticket.risk_level}
              </span>
            )}

            {isAdmin && ticket.low_confidence && (
              <span className="inline-flex items-center gap-0.5 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-full border bg-orange-50 text-orange-700 border-orange-200 animate-pulse">
                <AlertOctagon className="w-2.5 h-2.5" />
                Low Conf
              </span>
            )}

            {ticket.resolution?.automated && (
              <span className="inline-flex items-center gap-0.5 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200">
                <Zap className="w-2.5 h-2.5" />
                Auto
              </span>
            )}
          </div>

          {/* Title */}
          <p className={`
            text-xs font-semibold leading-snug truncate transition-colors
            ${isSelected ? 'text-primary' : 'text-slate-900 group-hover:text-primary'}
          `}>
            {ticket.title}
          </p>

          {/* Footer: priority + age */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${priorityDot[ticket.priority] || priorityDot.medium}`} />
              <span className="text-[9px] font-mono text-slate-400 uppercase">{ticket.priority}</span>
            </div>
            <div className="flex items-center gap-1 text-[9px] font-mono text-slate-400">
              <Clock className="w-2.5 h-2.5" />
              {formatAge(ticket.updatedAt)}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
