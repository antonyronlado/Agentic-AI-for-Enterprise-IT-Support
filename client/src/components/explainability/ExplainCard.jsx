import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Brain, ChevronDown, ChevronRight, AlertTriangle, CheckCircle,
  Info, Shield, GitMerge, Zap, Users, Activity,
} from 'lucide-react';

function ConfidenceBar({ value, className = '' }) {
  const color = value >= 80 ? '#10b981' : value >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          className="h-1.5 rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-[10px] font-mono tabular-nums w-7 text-right" style={{ color }}>{value}%</span>
    </div>
  );
}

function ConfidenceBadge({ value }) {
  const style =
    value >= 80 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
    value >= 60 ? 'bg-amber-50 text-amber-700 border-amber-200' :
    'bg-red-50 text-red-700 border-red-200';
  return (
    <span className={`inline-flex items-center gap-1 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-md border ${style}`}>
      {value}% conf
    </span>
  );
}

function ExpandableSection({ title, children, defaultOpen = false, badge = null }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-600 font-bold">{title}</span>
          {badge}
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-slate-100">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DecisionCard({ title, value, reasons = [], confidence, icon: Icon, colorClass, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
    >
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon className={`w-3.5 h-3.5 ${colorClass}`} />}
          <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500">{title}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-black ${colorClass}`}>{value}</span>
          {confidence != null && <ConfidenceBadge value={confidence} />}
          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown className="w-3 h-3 text-slate-300" />
          </motion.div>
        </div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-4 pb-3 border-t border-slate-50 space-y-2 pt-2">
              {confidence != null && <ConfidenceBar value={confidence} />}
              {reasons.length > 0 && (
                <ul className="space-y-1.5">
                  {reasons.map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <ChevronRight className="w-3 h-3 text-slate-300 mt-0.5 shrink-0" />
                      <span className="text-[10px] text-slate-600 leading-relaxed">{r}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function AgentTraceStep({ step, index, total }) {
  const isLast = index === total - 1;
  const AGENT_COLORS = {
    'Preprocessor':           'bg-slate-400',
    'DedupAgent':             'bg-violet-500',
    'TicketAnalyzer (BART)':  'bg-indigo-500',
    'RiskAgent':              'bg-amber-500',
    'EscalationAgent':        'bg-red-400',
    'ResolutionAgent (RAG)':  'bg-emerald-500',
    'CARS (RemediationAgent)':'bg-orange-500',
    'ExplainAgent':           'bg-blue-500',
  };
  const dotColor = AGENT_COLORS[step.agent] || 'bg-slate-400';

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06 }}
      className="relative flex gap-3"
    >
      <div className="flex flex-col items-center shrink-0">
        <div className={`w-2 h-2 rounded-full mt-0.5 shrink-0 ${dotColor}`} />
        {!isLast && <div className="w-px flex-1 bg-slate-100 mt-1" />}
      </div>
      <div className={`pb-${isLast ? '0' : '4'} space-y-0.5 min-w-0`}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded-md text-white ${dotColor}`}>
            {step.agent}
          </span>
          <span className="text-[9px] font-mono text-slate-400">Step {step.step}</span>
        </div>
        <p className="text-[10px] font-semibold text-slate-800">{step.action}</p>
        <p className="text-[9px] text-slate-500 leading-relaxed">{step.detail}</p>
      </div>
    </motion.div>
  );
}

export function ExplainCard({ explanation }) {
  if (!explanation) {
    return (
      <div className="py-12 text-center">
        <Brain className="w-8 h-8 text-slate-200 mx-auto mb-2" />
        <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">AI reasoning not yet available</p>
        <p className="text-[9px] text-slate-300 mt-1">Pipeline still running — check back in a moment</p>
      </div>
    );
  }

  const {
    priority, risk, escalation, deduplication, remediation,
    sentiment, sentiment_confidence, reasoning_trace,
    overall_ai_confidence, confidence_map,
    business_critical, multi_user_impact,
  } = explanation;

  const sentimentColor =
    sentiment === 'negative' ? 'text-red-600' :
    sentiment === 'positive' ? 'text-emerald-600' : 'text-slate-500';

  const confColor =
    overall_ai_confidence >= 80 ? 'text-emerald-600' :
    overall_ai_confidence >= 60 ? 'text-amber-600' : 'text-red-600';

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900">AI Decision Reasoning</p>
            <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider">
              Explainable AI · Agentic Workflow Platform
            </p>
          </div>
        </div>
        {overall_ai_confidence != null && (
          <div className="text-right">
            <p className={`text-2xl font-black tabular-nums leading-none ${confColor}`}>
              {overall_ai_confidence}%
            </p>
            <p className="text-[8px] font-mono text-slate-400 uppercase tracking-wider">Overall Confidence</p>
            <ConfidenceBar value={overall_ai_confidence} className="mt-1 w-20" />
          </div>
        )}
      </div>

      {/* ── Context flags ── */}
      {(business_critical || multi_user_impact) && (
        <div className="flex gap-2 flex-wrap">
          {business_critical && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-red-50 border border-red-200">
              <Activity className="w-3 h-3 text-red-500" />
              <span className="text-[9px] font-mono text-red-700 uppercase font-bold">Business Critical System</span>
            </div>
          )}
          {multi_user_impact && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-200">
              <Users className="w-3 h-3 text-amber-500" />
              <span className="text-[9px] font-mono text-amber-700 uppercase font-bold">Multi-User Impact</span>
            </div>
          )}
        </div>
      )}

      {/* ── Deduplication card ── */}
      {deduplication?.is_duplicate && (
        <DecisionCard
          title="Deduplication Detection"
          value="LINKED INCIDENT"
          reasons={deduplication.reasons}
          confidence={deduplication.confidence}
          icon={GitMerge}
          colorClass="text-violet-600"
        />
      )}

      {/* ── Decision cards ── */}
      <div className="space-y-2">
        {priority && (
          <DecisionCard
            title="Priority Classification"
            value={priority.value}
            reasons={priority.reasons}
            confidence={priority.confidence}
            icon={AlertTriangle}
            colorClass={
              priority.value === 'CRITICAL' || priority.value === 'HIGH' ? 'text-red-600' :
              priority.value === 'MEDIUM' ? 'text-amber-600' : 'text-emerald-600'
            }
          />
        )}
        {risk && (
          <DecisionCard
            title="Risk Assessment"
            value={risk.value}
            reasons={risk.reasons}
            confidence={risk.confidence}
            icon={Shield}
            colorClass={
              risk.value === 'HIGH' ? 'text-red-600' :
              risk.value === 'MEDIUM' ? 'text-amber-600' : 'text-emerald-600'
            }
          />
        )}
        {escalation && (
          <DecisionCard
            title="Escalation Decision"
            value={escalation.triggered ? 'ESCALATED' : 'NOT ESCALATED'}
            reasons={escalation.reasons}
            confidence={escalation.confidence}
            icon={escalation.triggered ? AlertTriangle : CheckCircle}
            colorClass={escalation.triggered ? 'text-red-600' : 'text-emerald-600'}
            defaultOpen={escalation.triggered}
          />
        )}
        {remediation && (
          <DecisionCard
            title="Remediation Decision"
            value={remediation.status?.toUpperCase().replace(/_/g, ' ')}
            reasons={remediation.reasons}
            confidence={remediation.confidence}
            icon={Zap}
            colorClass={
              remediation.status === 'executed' ? 'text-emerald-600' :
              remediation.status === 'pending_approval' ? 'text-amber-600' : 'text-slate-500'
            }
          />
        )}
        {sentiment && (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-3.5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Sentiment Analysis</p>
              <span className={`text-xs font-black uppercase ${sentimentColor}`}>{sentiment}</span>
            </div>
            {sentiment_confidence != null && <ConfidenceBar value={sentiment_confidence} />}
          </div>
        )}
      </div>

      {/* ── Agent Confidence Map ── */}
      {confidence_map && Object.values(confidence_map).some(v => v != null) && (
        <ExpandableSection title="Agent Confidence Map" defaultOpen={true}>
          <div className="space-y-2.5 pt-3">
            {Object.entries(confidence_map).filter(([, v]) => v != null).map(([key, val]) => (
              <div key={key}>
                <div className="flex justify-between mb-1">
                  <span className="text-[9px] font-mono text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[9px] font-mono text-slate-400">{val}%</span>
                </div>
                <ConfidenceBar value={val} />
              </div>
            ))}
          </div>
        </ExpandableSection>
      )}

      {/* ── Reasoning Trace ── */}
      {reasoning_trace && reasoning_trace.length > 0 && (
        <ExpandableSection
          title="Agent Reasoning Trace"
          defaultOpen={true}
          badge={
            <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 border border-indigo-100">
              {reasoning_trace.length} steps
            </span>
          }
        >
          <div className="space-y-0 pt-3">
            {Array.isArray(reasoning_trace) && reasoning_trace[0]?.agent ? (
              reasoning_trace.map((step, i) => (
                <AgentTraceStep key={i} step={step} index={i} total={reasoning_trace.length} />
              ))
            ) : (
              <ol className="space-y-2">
                {reasoning_trace.map((step, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-[9px] font-mono text-indigo-400 mt-0.5 shrink-0">{String(i + 1).padStart(2, '0')}</span>
                    <span className="text-[10px] text-slate-600">{step}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </ExpandableSection>
      )}
    </div>
  );
}
