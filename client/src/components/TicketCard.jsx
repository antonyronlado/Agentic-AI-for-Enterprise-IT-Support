import { motion } from 'motion/react';
import { StatusBadge } from './StatusBadge';
import { GitMerge, Users } from 'lucide-react';

function timeAgo(ts) {
  const diff = Math.floor((Date.now() - ts) / 60000);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
  return `${Math.floor(diff / 1440)}d ago`;
}

export function TicketCard({ ticket, role, isSelected, onClick }) {
  const riskLevel = ticket.risk_level || ticket.riskAssessment?.risk_level;
  const riskColor = riskLevel === 'high' ? 'bg-red-500' : riskLevel === 'medium' ? 'bg-amber-500' : 'bg-emerald-500';
  const isDuplicate = !!ticket.duplicate_of;
  const linkedCount = ticket.linked_count || 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      onClick={onClick}
      className={`relative p-3 rounded-xl border cursor-pointer transition-all duration-200 group ${
        isSelected
          ? 'border-indigo-300 bg-indigo-50/60 shadow-sm shadow-indigo-100'
          : 'border-slate-200/80 bg-white hover:border-slate-300 hover:shadow-sm'
      }`}
    >
      {role === 'admin' && riskLevel && (
        <div className={`absolute left-0 top-3 bottom-3 w-0.5 rounded-r-full ${riskColor}`} />
      )}

      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <StatusBadge status={ticket.status} size="sm" />
          {isDuplicate && (
            <span className="inline-flex items-center gap-0.5 text-[8px] font-mono uppercase px-1.5 py-0.5 rounded-md bg-violet-50 text-violet-600 border border-violet-200">
              <GitMerge className="w-2.5 h-2.5" /> Linked
            </span>
          )}
          {linkedCount > 0 && (
            <span className="inline-flex items-center gap-0.5 text-[8px] font-mono uppercase px-1.5 py-0.5 rounded-md bg-indigo-50 text-indigo-600 border border-indigo-200">
              <Users className="w-2.5 h-2.5" /> {linkedCount + 1} users
            </span>
          )}
        </div>
        <span className="text-[8px] font-mono text-slate-400 shrink-0">{timeAgo(ticket.updatedAt)}</span>
      </div>

      <p className="text-xs font-semibold text-slate-800 leading-snug line-clamp-2 mb-1">{ticket.title}</p>
      <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider truncate">{ticket.userEmail}</p>

      {role === 'admin' && ticket.confidence_score != null && (
        <div className="mt-1.5 flex items-center gap-1.5">
          <div className="flex-1 h-0.5 bg-slate-100 rounded-full">
            <div
              className="h-0.5 rounded-full"
              style={{
                width: `${ticket.confidence_score}%`,
                background: ticket.confidence_score >= 80 ? '#10b981' : ticket.confidence_score >= 60 ? '#f59e0b' : '#ef4444',
              }}
            />
          </div>
          <span className="text-[8px] font-mono text-slate-400">{ticket.confidence_score}%</span>
        </div>
      )}
    </motion.div>
  );
}