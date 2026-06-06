import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from './AuthGuard';
import { createTicket } from '../services/aiEngine';
import { toast } from 'sonner';
import {
  Send, Loader2, CheckCircle2, Brain, Cpu, Sparkles,
  Ticket as TicketIcon, TrendingUp, AlertTriangle, Bot, Paperclip,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { FileUploadPanel } from './multimodal/FileUploadPanel';

const API_BASE = import.meta.env.VITE_AI_ENGINE_URL || 'http://localhost:8000';

const PIPELINE_STEPS = [
  { id: 'create',  label: 'Submitting',  Icon: Send },
  { id: 'analyze', label: 'NLP Triage',  Icon: Brain },
  { id: 'save',    label: 'Finalizing',  Icon: Cpu },
];

function isPasswordReset(title, description) {
  const text = (title + ' ' + description).toLowerCase();
  return (
    text.includes('forgot') ||
    text.includes('reset password') ||
    text.includes('cannot login') ||
    text.includes("can't login") ||
    text.includes('cant login') ||
    text.includes('locked out') ||
    text.includes('lost password') ||
    text.includes('unable to login') ||
    text.includes('unable to sign')
  );
}

function PipelineStep({ step, currentStep, index, totalSteps }) {
  const stepIndex = PIPELINE_STEPS.findIndex(s => s.id === currentStep);
  const isActive  = currentStep === step.id;
  const isDone    = stepIndex > index;
  const { Icon } = step;
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300 ${isDone ? 'bg-emerald-100 text-emerald-600 scale-95' : isActive ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}>
        {isDone ? <CheckCircle2 className="w-3 h-3" /> : isActive ? <Loader2 className="w-3 h-3 animate-spin" /> : <Icon className="w-3 h-3" />}
      </div>
      <span className={`text-[9px] font-mono uppercase tracking-wide transition-colors ${isDone ? 'text-emerald-600' : isActive ? 'text-indigo-600 font-bold' : 'text-slate-400'}`}>{step.label}</span>
      {index < totalSteps - 1 && <div className={`w-5 h-px mx-1 transition-colors ${isDone ? 'bg-emerald-300' : 'bg-slate-200'}`} />}
    </div>
  );
}

function StatPill({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className={`w-4 h-4 rounded flex items-center justify-center ${color.bg}`}>
        <Icon className={`w-2.5 h-2.5 ${color.icon}`} />
      </div>
      <div>
        <p className={`text-sm font-black leading-none tracking-tight ${color.text}`}>{value}</p>
        <p className="text-[8px] font-mono text-slate-400 uppercase tracking-wider leading-none mt-0.5">{label}</p>
      </div>
    </div>
  );
}

export function AIInputPanel({ onTicketCreated, stats }) {
  const { user } = useAuth();
  const [title,          setTitle]         = useState('');
  const [description,    setDescription]   = useState('');
  const [targetWebsite,  setTargetWebsite] = useState('');
  const [websites,       setWebsites]      = useState([]);
  const [loading,        setLoading]       = useState(false);
  const [step,           setStep]          = useState(null);
  const [done,           setDone]          = useState(false);
  const [showUpload,     setShowUpload]    = useState(false);
  const textareaRef = useRef(null);

  const fetchSites = useCallback(() => {
    fetch(`${API_BASE}/websites/public`)
      .then(r => r.ok ? r.json() : [])
      .then(data => setWebsites(Array.isArray(data) ? data : []))
      .catch(() => setWebsites([]));
  }, []);

  useEffect(() => { fetchSites(); }, [fetchSites]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [description]);

  const showWebsiteDropdown = isPasswordReset(title, description);
  const canSubmit = title.trim().length > 2 && description.trim().length > 5 && !loading;

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!canSubmit || !user) return;
    setLoading(true);
    setDone(false);
    const toastId = toast.loading('Handing off to AI agents…');
    try {
      setStep('create');
      await new Promise(r => setTimeout(r, 300));
      setStep('analyze');
      await createTicket({
        title: title.trim(),
        description: description.trim(),
        userId: user.uid,
        userEmail: user.email,
        targetWebsite: targetWebsite || null,
      });
      setStep('save');
      await new Promise(r => setTimeout(r, 400));
      toast.success('Ticket submitted! Agentic workflow started.', { id: toastId });
      setDone(true);
      setTitle('');
      setDescription('');
      setTargetWebsite('');
      setShowUpload(false);
      onTicketCreated?.();
      setTimeout(() => setDone(false), 3500);
    } catch {
      toast.error('Failed to submit ticket', { id: toastId });
    } finally {
      setLoading(false);
      setStep(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  const handleInsertFromUpload = (text) => {
    setDescription(prev => prev ? `${prev}\n\n${text}` : text);
    setShowUpload(false);
  };

  return (
    <div className="flex flex-col gap-5 h-full">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-white" />
          </div>
          <div>
            <p className="text-[9px] font-mono uppercase tracking-widest text-slate-500">AI Status</p>
            <p className="text-xs font-semibold text-slate-800 leading-none">Online · Agentic Workflow Active</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <StatPill icon={TicketIcon}    label="Total"     value={stats?.total     ?? 0} color={{ bg: 'bg-slate-100',  icon: 'text-slate-500',   text: 'text-slate-700'   }} />
          <StatPill icon={TrendingUp}    label="Active"    value={stats?.active    ?? 0} color={{ bg: 'bg-blue-50',    icon: 'text-blue-500',    text: 'text-blue-700'    }} />
          <StatPill icon={AlertTriangle} label="Escalated" value={stats?.escalated ?? 0} color={{ bg: 'bg-red-50',     icon: 'text-red-500',     text: 'text-red-600'     }} />
          <StatPill icon={CheckCircle2}  label="Resolved"  value={stats?.resolved  ?? 0} color={{ bg: 'bg-emerald-50', icon: 'text-emerald-500', text: 'text-emerald-700' }} />
        </div>
      </div>

      <div className="section-divider" />

      <div className="flex-1 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-primary" />
          <p className="text-xs font-semibold text-slate-800">New Request</p>
          <span className="ml-auto text-[9px] font-mono text-slate-400 uppercase tracking-wider">⌘ + Enter</span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Brief subject line…"
            value={title}
            onChange={e => setTitle(e.target.value)}
            disabled={loading}
            required
            className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300/50 focus:border-indigo-300 transition-all duration-200 disabled:opacity-50"
          />

          <div className={`relative rounded-xl border bg-white overflow-hidden ai-input-focus ${loading ? 'opacity-70' : 'border-slate-200'}`}>
            <textarea
              ref={textareaRef}
              placeholder="Describe your issue — our AI agents will triage, assess risk, deduplicate, and resolve automatically…"
              value={description}
              onChange={e => setDescription(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              rows={4}
              className="w-full px-4 pt-4 pb-14 resize-none bg-transparent text-sm text-slate-800 leading-relaxed placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed"
            />
            <div className="absolute bottom-0 left-0 right-0 px-3 py-2 flex items-center justify-between bg-slate-50/80 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-mono text-slate-400">
                  {description.length > 0 ? `${description.length} chars` : 'AI agents: triage · risk · deduplicate · resolve'}
                </span>
                <button
                  type="button"
                  onClick={() => setShowUpload(v => !v)}
                  className={`flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded transition-colors ${showUpload ? 'bg-indigo-100 text-indigo-600' : 'text-slate-400 hover:text-slate-600'}`}
                >
                  <Paperclip className="w-2.5 h-2.5" />
                  Attach
                </button>
              </div>
              <button
                type="submit"
                disabled={!canSubmit}
                className={`h-7 px-3 rounded-md flex items-center gap-1.5 text-xs font-semibold transition-all duration-200 active:scale-95 ${done ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : canSubmit ? 'bg-primary text-white shadow-md shadow-primary/20 hover:bg-primary/90' : 'bg-slate-100 text-slate-400 cursor-not-allowed'}`}
              >
                {loading ? <><Loader2 className="w-3 h-3 animate-spin" /> Processing</> : done ? <><CheckCircle2 className="w-3 h-3" /> Submitted!</> : <><Send className="w-3 h-3" /> Send</>}
              </button>
            </div>
          </div>

          {/* Website dropdown — only for password reset tickets */}
          {showWebsiteDropdown && (
            <div style={{ border: '1px solid #a5b4fc', borderRadius: '10px', padding: '10px 12px', background: '#eef2ff' }}>
              <p style={{ fontSize: '11px', fontWeight: 700, color: '#4338ca', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                🌐 Which application needs a password reset?
              </p>
              {websites.length > 0 ? (
                <select
                  id="target-website-select"
                  value={targetWebsite}
                  onChange={e => setTargetWebsite(e.target.value)}
                  disabled={loading}
                  style={{ width: '100%', height: '34px', borderRadius: '6px', border: '1px solid #a5b4fc', padding: '0 8px', fontSize: '13px', background: 'white', color: '#1e293b' }}
                >
                  <option value="">Select application (optional)</option>
                  {websites.map(w => (
                    <option key={w.name} value={w.name}>{w.name}</option>
                  ))}
                </select>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <p style={{ fontSize: '11px', color: '#6b7280' }}>No applications loaded.</p>
                  <button type="button" onClick={fetchSites} style={{ fontSize: '11px', color: '#4338ca', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}>
                    Retry
                  </button>
                </div>
              )}
              <p style={{ fontSize: '10px', color: '#6366f1', marginTop: '4px' }}>
                AI agent will reset the password automatically.
              </p>
            </div>
          )}

          <AnimatePresence>
            {showUpload && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-3">
                  <p className="text-[9px] font-mono uppercase text-indigo-600 tracking-wider mb-2 flex items-center gap-1">
                    <Paperclip className="w-3 h-3" /> Multimodal Analysis — Screenshot or Log File
                  </p>
                  <FileUploadPanel onInsert={handleInsertFromUpload} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {loading && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                <div className="flex items-center gap-0.5 px-3 py-2.5 rounded-lg border border-indigo-100 bg-indigo-50/60">
                  {PIPELINE_STEPS.map((s, i) => (
                    <PipelineStep key={s.id} step={s} currentStep={step} index={i} totalSteps={PIPELINE_STEPS.length} />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </form>
      </div>

      <p className="text-[9px] text-center text-slate-400 font-mono uppercase tracking-wider">
        NexusDesk Enterprise AI-Native IT Operations Platform · v3.0
      </p>
    </div>
  );
}
