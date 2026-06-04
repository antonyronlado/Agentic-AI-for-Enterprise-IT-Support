import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { StatusBadge, StatusDot, AIActionLabel } from './StatusBadge';
import { Button } from '@/components/ui/button';
import {
  ChevronDown, Clock, Trash2, Zap,
  Ticket as TicketIcon, GitMerge, CheckCircle, AlertTriangle, ThumbsUp, ThumbsDown,
} from 'lucide-react';

function formatRelativeTime(ts) {
  const diffMs  = Date.now() - ts;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1)   return 'just now';
  if (diffMin < 60)  return `${diffMin}m ago`;
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
  return `${Math.floor(diffMin / 1440)}d ago`;
}

// ─────────────────────────────────────────────────────────
//  Inline detail panel shown when a ticket is expanded
// ─────────────────────────────────────────────────────────
function LinkedIncidentBanner({ ticket }) {
  const canonicalStatus = ticket.canonical_status || 'in_progress';
  const etaLabel = ticket.eta_label || 'Under investigation';
  const workaroundSteps = ticket.workaround_steps || [];
  const confidence = ticket.dedup_confidence ? Math.round(ticket.dedup_confidence * 100) : null;
  const employeeResponse = ticket.employee_response || '';

  const statusColor =
    canonicalStatus === 'resolved'  ? 'text-emerald-600 bg-emerald-50 border-emerald-200' :
    canonicalStatus === 'escalated' ? 'text-red-600 bg-red-50 border-red-200' :
    'text-amber-600 bg-amber-50 border-amber-200';

  // Extract the actual solution text from employee_response (skip the header line)
  const solutionText = employeeResponse
    ? employeeResponse.replace(/^Linked Incident Detected\n/, '').trim()
    : '';

  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50/60 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-violet-100">
        <GitMerge className="w-3.5 h-3.5 text-violet-600" />
        <p className="text-[10px] font-bold text-violet-800 uppercase tracking-wider">Linked Incident Detected</p>
        {confidence && (
          <span className="ml-auto text-[8px] font-mono px-1.5 py-0.5 rounded bg-violet-100 text-violet-600 border border-violet-200">
            {confidence}% match
          </span>
        )}
      </div>
      <div className="px-4 py-3 space-y-3">
        <p className="text-[10px] text-violet-700">
          Your issue has been identified as part of an existing incident currently under investigation.
          You have been automatically subscribed to resolution updates.
        </p>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-white border border-violet-100 px-3 py-2">
            <p className="text-[8px] font-mono uppercase text-slate-400 tracking-wider mb-0.5">Incident Status</p>
            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${statusColor}`}>
              {canonicalStatus.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="rounded-lg bg-white border border-violet-100 px-3 py-2">
            <p className="text-[8px] font-mono uppercase text-slate-400 tracking-wider mb-0.5">Estimated Resolution</p>
            <p className="text-[9px] text-slate-700 font-semibold leading-snug">{etaLabel}</p>
          </div>
        </div>

        {/* Show the AI solution — from workaround steps or the full employee response */}
        {workaroundSteps.length > 0 ? (
          <div className="rounded-lg bg-white border border-violet-100 p-3 space-y-1.5">
            <p className="text-[9px] font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-emerald-500" /> Suggested Workaround
            </p>
            {workaroundSteps.slice(0, 6).map((step, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-[8px] font-mono text-violet-400 mt-0.5 shrink-0">{i + 1}.</span>
                <span className="text-[10px] text-slate-700 leading-snug">{step}</span>
              </div>
            ))}
          </div>
        ) : solutionText ? (
          <div className="rounded-lg bg-white border border-indigo-100 p-3 space-y-1.5">
            <p className="text-[9px] font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1">
              <Zap className="w-3 h-3 text-indigo-500" /> AI Solution
            </p>
            <div className="text-[10px] text-slate-700 leading-relaxed whitespace-pre-line">
              {solutionText}
            </div>
          </div>
        ) : (
          <div className="rounded-lg bg-amber-50 border border-amber-100 p-3">
            <p className="text-[10px] text-amber-700 leading-snug">
              Our team is actively investigating this incident. A solution will be shared as soon as it is available.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function TicketDetailInline({ ticket, onFeedback }) {
  const statusKey = ticket.status || 'open';
  const isLinked  = statusKey === 'linked';

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.22 }}
      className="mt-3 rounded-xl border border-slate-100 bg-slate-50/70 overflow-hidden"
    >
      <div className="px-4 py-3 space-y-3">
        <div>
          <p className="text-[9px] font-mono uppercase tracking-widest text-slate-400 mb-1.5">Your Request</p>
          <p className="text-sm text-slate-700 leading-relaxed">{ticket.description}</p>
        </div>

        <div className="section-divider" />

        {isLinked ? (
          <LinkedIncidentBanner ticket={ticket} />
        ) : ticket.employee_response ? (
          <div className="space-y-3">
            <div className="rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-violet-50/40 p-4 space-y-2">
              <div className="flex items-center gap-1.5">
                <Zap className="w-3 h-3 text-indigo-500" />
                <p className="text-[9px] font-mono uppercase tracking-widest text-indigo-600">AI Response</p>
              </div>
              <div className="text-sm text-slate-800 leading-relaxed whitespace-pre-line">
                {ticket.employee_response}
              </div>
            </div>
            {statusKey === 'resolved' && onFeedback && (
              <div className="flex items-center gap-2">
                <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider">Was this helpful?</p>
                <button
                  onClick={() => onFeedback(ticket._id || ticket.id, 'positive')}
                  className="flex items-center gap-1 text-[9px] font-mono px-2 py-1 rounded-lg border border-emerald-200 text-emerald-600 hover:bg-emerald-50 transition-colors"
                >
                  <ThumbsUp className="w-3 h-3" /> Yes
                </button>
                <button
                  onClick={() => onFeedback(ticket._id || ticket.id, 'negative')}
                  className="flex items-center gap-1 text-[9px] font-mono px-2 py-1 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                >
                  <ThumbsDown className="w-3 h-3" /> No
                </button>
              </div>
            )}
          </div>
        ) : statusKey === 'failed' ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-center">
            <p className="text-xs text-rose-700 font-mono">
              An error occurred — our IT team has been notified and will review this ticket manually.
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white/70 p-4">
            <div className="flex items-center gap-2">
              <motion.div
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
                className="w-1.5 h-1.5 rounded-full bg-violet-500"
              />
              <p className="text-xs text-slate-500 font-mono">
                AI agents are working on this — usually resolves in under a minute
              </p>
            </div>
          </div>
        )}

        <p className="text-[9px] font-mono text-slate-400">
          Submitted {new Date(ticket.createdAt).toLocaleString()}
          {' · '}
          Updated {new Date(ticket.updatedAt).toLocaleString()}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────
//  Single timeline row
// ─────────────────────────────────────────────────────────
function TimelineItem({ ticket, isExpanded, onToggle, onDelete, onFeedback }) {
  const statusKey = ticket.status || 'open';
  const ticketId  = ticket._id || ticket.id || '';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8, scale: 0.98 }}
      transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
      className="timeline-line"
    >
      {/* ── Row ─────────────────────────────────────────── */}
      <div
        className={`
          group relative flex items-start gap-3 cursor-pointer
          rounded-xl px-4 py-3.5 transition-all duration-200
          ${isExpanded
            ? 'bg-white shadow-[0_2px_16px_rgba(0,0,0,0.06)] border border-slate-200/80'
            : 'hover:bg-white/70 hover:shadow-[0_1px_8px_rgba(0,0,0,0.05)] border border-transparent'}
        `}
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && onToggle()}
      >
        {/* Left: Status dot */}
        <div className="pt-1 shrink-0">
          <StatusDot status={statusKey} size="md" />
        </div>

        {/* Center: Info */}
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[9px] font-mono text-slate-400 uppercase">
              #{ticketId.slice(0, 8)}
            </span>
            <StatusBadge status={statusKey} size="sm" />
          </div>
          <p className={`
            text-sm font-semibold leading-snug truncate transition-colors
            ${isExpanded ? 'text-primary' : 'text-slate-900 group-hover:text-primary'}
          `}>
            {ticket.title}
          </p>
          <AIActionLabel status={statusKey} automated={ticket.resolution?.automated} />
        </div>

        {/* Right: Time + actions */}
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <div className="flex items-center gap-1 text-[9px] font-mono text-slate-400">
            <Clock className="w-3 h-3" />
            {formatRelativeTime(ticket.updatedAt)}
          </div>
          {onDelete && (
            <button
              onClick={e => { e.stopPropagation(); onDelete(ticketId); }}
              className="opacity-0 group-hover:opacity-100 w-6 h-6 rounded-md flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
              aria-label="Delete ticket"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-slate-400 group-hover:text-primary transition-colors"
          >
            <ChevronDown className="w-4 h-4" />
          </motion.div>
        </div>
      </div>

      {/* ── Expandable detail ───────────────────────────── */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden px-4"
          >
            <TicketDetailInline ticket={ticket} onFeedback={onFeedback} />
            <div className="h-4" />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────
//  Filter pills
// ─────────────────────────────────────────────────────────
const FILTERS = [
  { key: 'all',       label: 'All' },
  { key: 'active',    label: 'Active' },
  { key: 'resolved',  label: 'Resolved' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'linked',    label: 'Linked' },
];

function isActive(ticket) {
  return !['resolved', 'escalated', 'failed', 'linked'].includes(ticket.status);
}

function filterTickets(tickets, key) {
  if (key === 'all')       return tickets;
  if (key === 'active')    return tickets.filter(isActive);
  if (key === 'resolved')  return tickets.filter(t => t.status === 'resolved');
  if (key === 'escalated') return tickets.filter(t => t.status === 'escalated');
  if (key === 'linked')    return tickets.filter(t => t.status === 'linked');
  return tickets;
}




// ─────────────────────────────────────────────────────────
//  Main component
// ─────────────────────────────────────────────────────────
export function TicketTimeline({ tickets, onDelete, onFeedback, loading }) {
  const [filter,   setFilter]   = useState('all');
  const [expanded, setExpanded] = useState(null);

  const filtered = filterTickets(tickets, filter);

  const toggleExpand = (id) => {
    setExpanded(prev => prev === id ? null : id);
  };

  return (
    <div className="flex flex-col gap-4 h-full">

      {/* ── Filter strip ─────────────────────────────────── */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {FILTERS.map(f => {
          const count = filterTickets(tickets, f.key).length;
          const active = filter === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`
                h-7 px-3 rounded-lg text-xs font-medium transition-all duration-150
                ${active
                  ? 'bg-primary text-white shadow-md shadow-primary/20'
                  : 'bg-white border border-slate-200 text-slate-600 hover:border-primary/30 hover:text-primary'}
              `}
            >
              {f.label}
              <span className={`ml-1.5 text-[9px] font-mono ${active ? 'opacity-70' : 'text-slate-400'}`}>
                {count}
              </span>
            </button>
          );
        })}

        <div className="ml-auto flex items-center gap-1.5 text-[9px] font-mono text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Live sync
        </div>
      </div>

      {/* ── Timeline list ─────────────────────────────────── */}
      <div className="flex-1 space-y-1">
        <AnimatePresence mode="popLayout" initial={false}>
          {filtered.length > 0 ? (
            filtered.map(ticket => {
              const id = ticket._id || ticket.id;
              return (
                <TimelineItem
                  key={id}
                  ticket={ticket}
                  isExpanded={expanded === id}
                  onToggle={() => toggleExpand(id)}
                  onDelete={onDelete}
                  onFeedback={onFeedback}
                />
              );
            })
          ) : !loading ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-24 text-center"
            >
              <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mb-4 float">
                <TicketIcon className="w-7 h-7 text-slate-300" />
              </div>
              <p className="text-slate-500 font-semibold text-sm">No tickets here</p>
              <p className="text-slate-400 font-mono text-[10px] uppercase tracking-widest mt-1">
                {filter === 'all'
                  ? 'Describe your first issue →'
                  : `No ${filter} tickets`}
              </p>
              {filter !== 'all' && (
                <button
                  onClick={() => setFilter('all')}
                  className="mt-3 text-[10px] font-mono text-primary underline uppercase tracking-wider"
                >
                  Show all
                </button>
              )}
            </motion.div>
          ) : (
            // Loading skeletons
            <motion.div
              key="skeletons"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-2"
            >
              {[1, 2, 3].map(i => (
                <div
                  key={i}
                  className="h-16 rounded-xl bg-white border border-slate-100 shimmer"
                  style={{ animationDelay: `${i * 0.1}s` }}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
