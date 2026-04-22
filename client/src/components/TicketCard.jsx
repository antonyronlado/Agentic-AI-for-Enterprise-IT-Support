import { motion } from 'motion/react';
import { Clock, AlertCircle, Cpu, ChevronRight, ShieldAlert, CheckCircle2, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const statusConfig = {
  open: { label: 'Open', color: 'bg-blue-500', badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  analyzing: { label: 'Analyzing', color: 'bg-purple-500', badge: 'bg-purple-500/10 text-purple-400 border-purple-500/20 animate-pulse' },
  resolving: { label: 'Resolving', color: 'bg-amber-500', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  risk_assessment: { label: 'Risk Check', color: 'bg-orange-500', badge: 'bg-orange-500/10 text-orange-400 border-orange-500/20' },
  resolved: { label: 'Resolved', color: 'bg-emerald-500', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  escalated: { label: 'Escalated', color: 'bg-red-500', badge: 'bg-red-500/10 text-red-400 border-red-500/20' },
};

const priorityConfig = {
  low: { color: 'text-white/40', dot: 'bg-white/30' },
  medium: { color: 'text-blue-400', dot: 'bg-blue-400' },
  high: { color: 'text-amber-400', dot: 'bg-amber-400' },
  critical: { color: 'text-red-400', dot: 'bg-red-400' },
};

export function TicketCard({ ticket, onClick, onDelete }) {
  const status = statusConfig[ticket.status] || statusConfig.open;
  const priority = priorityConfig[ticket.priority] || priorityConfig.medium;
  const hasAI = !!ticket.analysis;
  const hasRisk = !!ticket.riskAssessment;
  const confidence = ticket.analysis?.confidenceScore;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01, y: -1 }}
      transition={{ duration: 0.2 }}
      className="cursor-pointer group relative"
      onClick={onClick}
    >
      <div className="relative rounded-xl border border-white/5 bg-white/[0.025] backdrop-blur-sm overflow-hidden transition-all duration-200 hover:border-white/10 hover:bg-white/[0.04] hover:shadow-lg hover:shadow-black/20">
        <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${status.color}`} />

        <div className="pl-5 pr-4 pt-4 pb-3 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1 flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[9px] font-mono text-white/30 uppercase tracking-wider">
                  #{ticket._id ? ticket._id.slice(0, 8) : ticket.id?.slice(0, 8)}
                </span>
                <span className={`inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-full border ${status.badge}`}>
                  {ticket.status === 'analyzing' && <span className="w-1 h-1 rounded-full bg-current animate-pulse" />}
                  {status.label}
                </span>
              </div>
              <p className="text-sm font-semibold text-white leading-snug truncate group-hover:text-primary transition-colors">
                {ticket.title}
              </p>
            </div>

            <div className={`flex items-center gap-1.5 text-[10px] font-mono uppercase shrink-0 ${priority.color}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${priority.dot}`} />
              {ticket.priority}
            </div>
          </div>

          <p className="text-xs text-white/40 line-clamp-2 leading-relaxed">
            {ticket.description}
          </p>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-white/5 text-white/40 border border-white/5">
              {ticket.category}
            </span>

            {hasAI && (
              <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20">
                <Cpu className="w-2.5 h-2.5" />
                AI Analyzed
                {confidence !== undefined && (
                  <span className="text-primary/60">· {Math.round(confidence * 100)}%</span>
                )}
              </span>
            )}

            {hasRisk && ticket.riskAssessment?.securityRisk && (
              <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 border border-red-500/20">
                <ShieldAlert className="w-2.5 h-2.5" />
                Security Risk
              </span>
            )}

            {ticket.status === 'resolved' && (
              <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-2.5 h-2.5" />
                {ticket.resolution?.automated ? 'Auto-Resolved' : 'Resolved'}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between px-5 py-2.5 border-t border-white/5 bg-black/20">
          <div className="flex items-center gap-1 text-[9px] font-mono text-white/25">
            <Clock className="w-2.5 h-2.5" />
            {new Date(ticket.updatedAt).toLocaleString()}
          </div>
          <div className="flex items-center gap-2">
            {onDelete && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(ticket._id || ticket.id);
                }}
                className="text-white/30 hover:text-red-400 hover:bg-red-500/10 h-6 w-6"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            )}
            <div className="flex items-center gap-1 text-[9px] font-mono text-white/30 group-hover:text-primary transition-colors">
              VIEW <ChevronRight className="w-3 h-3" />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
