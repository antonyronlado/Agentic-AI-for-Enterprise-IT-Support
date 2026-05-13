import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Shield, CheckCircle, XCircle, RotateCcw, Clock, AlertTriangle,
  ChevronDown, Activity, User, Bot,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { approveAction, rejectAction, rollbackAction } from '../../services/aiEngine';
import { toast } from 'sonner';

const STATUS_CONFIG = {
  pending_approval: { label: 'Awaiting Approval', icon: Clock,       color: 'text-amber-600',   bg: 'bg-amber-50 border-amber-200'   },
  queued:           { label: 'Queued',             icon: Clock,       color: 'text-blue-600',    bg: 'bg-blue-50 border-blue-200'     },
  approved:         { label: 'Approved',           icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200'},
  executed:         { label: 'Executed',           icon: CheckCircle, color: 'text-indigo-600',  bg: 'bg-indigo-50 border-indigo-200' },
  rejected:         { label: 'Rejected',           icon: XCircle,     color: 'text-red-600',     bg: 'bg-red-50 border-red-200'       },
  rolled_back:      { label: 'Rolled Back',        icon: RotateCcw,   color: 'text-slate-600',   bg: 'bg-slate-50 border-slate-200'   },
};

const RISK_BADGE = {
  LOW:    'bg-emerald-50 text-emerald-700 border-emerald-200',
  MEDIUM: 'bg-amber-50 text-amber-700 border-amber-200',
  HIGH:   'bg-red-50 text-red-700 border-red-200',
};

function AuditTimeline({ events }) {
  const [open, setOpen] = useState(false);
  if (!events?.length) return null;

  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-slate-100/60 transition-colors"
      >
        <p className="text-[9px] font-mono uppercase text-slate-500 tracking-wider flex items-center gap-1.5">
          <Activity className="w-3 h-3" /> Audit Trail
          <span className="text-indigo-500 font-bold">({events.length} events)</span>
        </p>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2 border-t border-slate-100 pt-2">
              {events.map((ev, i) => {
                const isHuman = ev.actor === 'HumanApproval';
                const Icon = isHuman ? User : Bot;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="flex items-start gap-2"
                  >
                    <div className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${isHuman ? 'bg-indigo-100' : 'bg-slate-100'}`}>
                      <Icon className={`w-2.5 h-2.5 ${isHuman ? 'text-indigo-500' : 'text-slate-400'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[9px] text-slate-700 leading-snug">{ev.event}</p>
                      <p className="text-[8px] font-mono text-slate-400 mt-0.5">
                        {ev.actor} · {new Date(ev.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function AutoActionPanel({ action, ticketId, onUpdate }) {
  const [busy, setBusy]       = useState(false);
  const [confirm, setConfirm] = useState(null);
  const [auditData, setAuditData] = useState(null);

  if (!action) return null;

  const docId    = action.action_doc_id;
  const status   = action.status;
  const cfg      = STATUS_CONFIG[status] || STATUS_CONFIG.executed;
  const StatusIcon = cfg.icon;
  const riskLevel  = action.risk_level || 'LOW';
  const confidence = action.confidence;
  const auditEvents = auditData?.audit_trail || action.audit_events?.map(e => ({
    event: e, timestamp: Date.now(), actor: 'CARS'
  }));

  const handle = async (fn, label) => {
    setBusy(true);
    setConfirm(null);
    try {
      const result = await fn();
      if (result?.action?.audit_trail) {
        setAuditData(result.action);
      }
      toast.success(`${label} successful`);
      onUpdate?.();
    } catch (e) {
      toast.error(e.message || `${label} failed`);
    } finally {
      setBusy(false);
    }
  };

  const confColor = confidence >= 80 ? '#10b981' : confidence >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-indigo-50/30 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm">
          <Shield className="w-3.5 h-3.5 text-white" />
        </div>
        <div className="flex-1">
          <p className="text-xs font-bold text-slate-900">Controlled Automated Remediation System</p>
          <p className="text-[8px] font-mono text-slate-400 uppercase tracking-wider">CARS · Human-in-the-Loop · Audit Logged</p>
        </div>
        <span className={`flex items-center gap-1 text-[8px] font-mono uppercase px-2 py-1 rounded-lg border ${cfg.bg} ${cfg.color}`}>
          <StatusIcon className="w-2.5 h-2.5" />
          {cfg.label}
        </span>
      </div>

      <div className="p-4 space-y-4">
        {/* Action summary */}
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 flex-1">
            <p className="text-sm font-bold text-slate-900">{action.name}</p>
            <p className="text-[10px] text-slate-500 leading-relaxed">{action.description}</p>
          </div>
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <span className={`text-[8px] font-mono uppercase px-2 py-0.5 rounded border ${RISK_BADGE[riskLevel] || RISK_BADGE.LOW}`}>
              {riskLevel} risk
            </span>
            {confidence && (
              <span className="text-[9px] font-mono" style={{ color: confColor }}>
                {confidence}% confident
              </span>
            )}
          </div>
        </div>

        {/* Confidence bar */}
        {confidence && (
          <div className="space-y-0.5">
            <p className="text-[9px] font-mono uppercase text-slate-400 tracking-wider">AI Match Confidence</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
                <motion.div
                  className="h-1 rounded-full"
                  style={{ background: confColor }}
                  initial={{ width: 0 }}
                  animate={{ width: `${confidence}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                />
              </div>
              <span className="text-[9px] font-mono tabular-nums" style={{ color: confColor }}>{confidence}%</span>
            </div>
          </div>
        )}

        {/* Execution steps */}
        {action.steps?.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[9px] font-mono uppercase text-slate-400 tracking-wider">Execution Plan</p>
            {action.steps.map((step, i) => {
              const isDone = status === 'executed' || status === 'rolled_back';
              return (
                <div key={i} className="flex items-start gap-2">
                  <div className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${isDone ? 'bg-emerald-100' : 'bg-slate-100'}`}>
                    {isDone
                      ? <CheckCircle className="w-2.5 h-2.5 text-emerald-500" />
                      : <span className="text-[7px] font-mono text-slate-400">{i + 1}</span>
                    }
                  </div>
                  <span className="text-[10px] text-slate-600 leading-snug">{step}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Approval gate */}
        {action.needs_approval && status === 'pending_approval' && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 space-y-2.5">
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <p className="text-[10px] font-bold text-amber-800">Human Approval Required</p>
            </div>
            <p className="text-[9px] text-amber-700">
              CARS classified this as a <strong>{riskLevel.toLowerCase()}-risk</strong> action.
              IT administrator approval is required before execution per enterprise policy.
            </p>
            <div className="flex gap-2">
              {confirm === 'approve' ? (
                <>
                  <Button size="sm" disabled={busy} onClick={() => handle(() => approveAction(docId), 'Approval')} className="flex-1 h-7 text-[10px] bg-emerald-500 hover:bg-emerald-600 text-white">
                    {busy ? 'Executing…' : 'Confirm Approve'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setConfirm(null)} className="h-7 text-[10px]">Cancel</Button>
                </>
              ) : confirm === 'reject' ? (
                <>
                  <Button size="sm" disabled={busy} onClick={() => handle(() => rejectAction(docId), 'Rejection')} className="flex-1 h-7 text-[10px] bg-red-500 hover:bg-red-600 text-white">
                    Confirm Reject
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setConfirm(null)} className="h-7 text-[10px]">Cancel</Button>
                </>
              ) : (
                <>
                  <Button size="sm" onClick={() => setConfirm('approve')} className="flex-1 h-7 text-[10px] bg-emerald-500 hover:bg-emerald-600 text-white">
                    <CheckCircle className="w-3 h-3 mr-1" /> Approve
                  </Button>
                  <Button size="sm" onClick={() => setConfirm('reject')} variant="outline" className="flex-1 h-7 text-[10px] border-red-200 text-red-600 hover:bg-red-50">
                    <XCircle className="w-3 h-3 mr-1" /> Reject
                  </Button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Rollback */}
        {status === 'executed' && (
          <div className="space-y-2">
            {confirm === 'rollback' ? (
              <div className="flex gap-2">
                <Button size="sm" disabled={busy} onClick={() => handle(() => rollbackAction(docId), 'Rollback')} className="flex-1 h-7 text-[10px] bg-slate-700 hover:bg-slate-800 text-white">
                  {busy ? 'Rolling back…' : 'Confirm Rollback'}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setConfirm(null)} className="h-7 text-[10px]">Cancel</Button>
              </div>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setConfirm('rollback')} className="w-full h-7 text-[10px] border-slate-300 text-slate-600 hover:bg-slate-50">
                <RotateCcw className="w-3 h-3 mr-1.5" /> Rollback Action
              </Button>
            )}
          </div>
        )}

        {/* Rollback plan */}
        {action.rollback_plan && (
          <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
            <p className="text-[9px] font-mono uppercase text-slate-400 tracking-wider mb-1">Rollback Plan</p>
            <p className="text-[9px] text-slate-600 leading-relaxed">{action.rollback_plan}</p>
          </div>
        )}

        {/* Audit trail */}
        <AuditTimeline events={auditEvents} />
      </div>
    </div>
  );
}
