import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bot, X, Copy, CheckCheck, ChevronRight, Zap, AlertTriangle, MessageSquare, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getCopilotSuggestions } from '../../services/copilotService';
import { toast } from 'sonner';

function ConfidenceBar({ value }) {
  const color = value >= 80 ? '#10b981' : value >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
        <motion.div className="h-1 rounded-full" style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.6 }} />
      </div>
      <span className="text-[9px] font-mono tabular-nums" style={{ color }}>{value}%</span>
    </div>
  );
}

export function CopilotPanel({ ticket, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [draftText, setDraftText] = useState('');

  useEffect(() => {
    if (!ticket) return;
    setLoading(true);
    setData(null);
    getCopilotSuggestions({
      ticket_id: ticket._id || ticket.id,
      title: ticket.title,
      description: ticket.description,
      analysis: ticket.analysis,
      risk: ticket.riskAssessment,
    })
      .then(d => { setData(d); setDraftText(d.draft_response || ''); })
      .catch(() => toast.error('Copilot suggestions failed'))
      .finally(() => setLoading(false));
  }, [ticket?._id || ticket?.id]);

  const handleCopy = () => {
    navigator.clipboard.writeText(draftText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const escColor =
    data?.escalation_priority === 'high' ? 'text-red-600 bg-red-50 border-red-200' :
    data?.escalation_priority === 'medium' ? 'text-amber-600 bg-amber-50 border-amber-200' :
    'text-emerald-600 bg-emerald-50 border-emerald-200';

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="w-80 shrink-0 border-l border-black/[0.06] bg-white flex flex-col h-[calc(100vh-3.5rem)] sticky top-14 overflow-hidden"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-violet-50">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm">
            <Bot className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-900">AI Copilot</p>
            <p className="text-[8px] font-mono text-slate-400 uppercase tracking-wider">Real-time Assistance</p>
          </div>
        </div>
        <button onClick={onClose} className="w-6 h-6 rounded-md flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading ? (
          <div className="space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="h-20 rounded-xl bg-slate-100 animate-pulse" />
            ))}
          </div>
        ) : !data ? null : (
          <>
            {data.overall_confidence != null && (
              <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-3">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-[9px] font-mono uppercase text-indigo-600 tracking-wider">Copilot Confidence</p>
                  <span className="text-sm font-black text-indigo-700 tabular-nums">{data.overall_confidence}%</span>
                </div>
                <ConfidenceBar value={data.overall_confidence} />
              </div>
            )}

            {data.escalation_priority && (
              <div className={`rounded-xl border p-3 ${escColor}`}>
                <div className="flex items-center gap-1.5 mb-1">
                  <AlertTriangle className="w-3 h-3" />
                  <p className="text-[9px] font-mono uppercase tracking-wider font-bold">Escalation Recommendation</p>
                </div>
                <p className="text-[10px] font-bold capitalize">{data.escalation_priority.toUpperCase()} Priority</p>
                <p className="text-[9px] mt-0.5 opacity-80">{data.escalation_reason}</p>
              </div>
            )}

            {data.suggested_fixes?.length > 0 && (
              <div className="space-y-2">
                <p className="text-[9px] font-mono uppercase text-slate-500 tracking-wider flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Suggested Fixes
                </p>
                {data.suggested_fixes.map((fix, i) => (
                  <div key={i} className="rounded-xl border border-slate-100 bg-slate-50 p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[10px] font-bold text-slate-700 truncate">{fix.source_title}</p>
                      <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded-md border ${fix.confidence >= 80 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : fix.confidence >= 60 ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                        {fix.confidence}%
                      </span>
                    </div>
                    <ConfidenceBar value={fix.confidence} />
                    {fix.steps?.slice(0, 3).map((step, j) => (
                      <div key={j} className="flex items-start gap-1.5">
                        <ChevronRight className="w-3 h-3 text-slate-300 mt-0.5 shrink-0" />
                        <p className="text-[9px] text-slate-600">{step}</p>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {data.similar_tickets?.length > 0 && (
              <div className="space-y-2">
                <p className="text-[9px] font-mono uppercase text-slate-500 tracking-wider flex items-center gap-1">
                  <BookOpen className="w-3 h-3" /> Similar Resolved Cases
                </p>
                {data.similar_tickets.map((t, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-slate-100 bg-slate-50">
                    <p className="text-[10px] text-slate-700 truncate">{t.title}</p>
                    <span className={`text-[8px] font-mono px-1 py-0.5 rounded border ${t.confidence >= 70 ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                      {t.confidence}%
                    </span>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-2">
              <p className="text-[9px] font-mono uppercase text-slate-500 tracking-wider flex items-center gap-1">
                <MessageSquare className="w-3 h-3" /> Draft Response
              </p>
              <textarea
                value={draftText}
                onChange={e => setDraftText(e.target.value)}
                className="w-full text-[10px] text-slate-700 leading-relaxed border border-slate-200 rounded-xl p-3 bg-slate-50 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-transparent"
                rows={7}
              />
              <Button
                size="sm"
                onClick={handleCopy}
                className="w-full h-8 text-[10px] font-mono uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {copied ? <><CheckCheck className="w-3 h-3 mr-1.5" /> Copied!</> : <><Copy className="w-3 h-3 mr-1.5" /> Copy Response</>}
              </Button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}