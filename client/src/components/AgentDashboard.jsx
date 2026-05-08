import { useEffect, useState } from 'react';
import { useAuth } from './AuthGuard';
import { getTickets, updateTicket, getLogs } from '../services/aiEngine';
import { TicketCard } from './TicketCard';
import { AnalysisSection, RiskSummaryCard, RiskAssessmentPanel } from './AnalysisSection';
import { StatusBadge } from './StatusBadge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  Activity, LogOut, Shield, Brain, TerminalSquare,
  LayoutDashboard, CheckCircle, BookPlus, AlertOctagon,
  XCircle, Clock, CheckCircle2, Zap,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const API_URL = import.meta.env.VITE_AI_ENGINE_URL || 'http://localhost:8000';

async function learnFromTicket(ticket, resolution) {
  const res = await fetch(`${API_URL}/learn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticket_id:   ticket._id || ticket.id,
      title:       ticket.title,
      description: ticket.description,
      steps:       resolution?.steps || [],
      result:      resolution?.result || 'Resolved.',
      category:    ticket.category || 'other',
    }),
  });
  return res.json();
}

function isSlaWarning(ticket) {
  const diffMin = Math.floor((Date.now() - ticket.updatedAt) / 60000);
  if (ticket.status === 'open'        && diffMin > 30)  return true;
  if (ticket.status === 'in_progress' && diffMin > 240) return true;
  return false;
}

function TimelineEvent({ event }) {
  return (
    <div className="relative pl-7">
      <div className="absolute left-0 top-1 w-3 h-3 rounded-full bg-white border-2 border-primary z-10" />
      <p className="text-[9px] font-mono text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</p>
      <p className="text-[10px] font-bold uppercase text-primary">{event.status?.replace(/_/g, ' ')}</p>
      <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{event.message}</p>
    </div>
  );
}

function HeaderStat({ label, value, color }) {
  return (
    <div className="text-center px-3 border-l border-slate-200 first:border-l-0">
      <p className={`text-base font-black leading-none ${color}`}>{value}</p>
      <p className="text-[8px] font-mono text-slate-400 uppercase tracking-wider mt-0.5">{label}</p>
    </div>
  );
}

export function AgentDashboard() {
  const { profile, signOut } = useAuth();
  const [tickets, setTickets]         = useState([]);
  const [selectedTicket, setSelected] = useState(null);
  const [activeTab, setActiveTab]     = useState('ai_analysis');
  const [viewMode, setViewMode]       = useState('tickets');
  const [logs, setLogs]               = useState([]);
  const [resolving, setResolving]     = useState(null);

  const fetchTickets = async () => {
    try {
      const data = await getTickets(null, 'admin');
      setTickets(data);
      if (selectedTicket) {
        const up = data.find(t => (t._id || t.id) === (selectedTicket._id || selectedTicket.id));
        if (up) setSelected(up);
      }
    } catch { toast.error('Failed to load tickets'); }
  };

  const fetchLogs = async () => {
    try { setLogs(await getLogs(150)); } catch { toast.error('Failed to load logs'); }
  };

  useEffect(() => {
    if (viewMode === 'tickets') {
      fetchTickets();
      const iv = setInterval(fetchTickets, 5000);
      return () => clearInterval(iv);
    } else {
      fetchLogs();
      const iv = setInterval(fetchLogs, 5000);
      return () => clearInterval(iv);
    }
  }, [viewMode]);

  const handleMarkResolved = async () => {
    if (!selectedTicket) return;
    const tId = selectedTicket._id || selectedTicket.id;
    setResolving(tId);
    try {
      await updateTicket(tId, {
        status: 'resolved',
        updatedAt: Date.now(),
        history: [...(selectedTicket.history || []), {
          timestamp: Date.now(), status: 'resolved',
          message: 'Agent manually verified and marked as resolved.',
        }],
      });
      toast.success('Ticket marked as resolved');
      fetchTickets();
    } catch { toast.error('Failed to resolve ticket'); }
    finally { setResolving(null); }
  };

  const handleLearnFromTicket = async (t) => {
    try {
      const result = await learnFromTicket(t, t.resolution);
      if (result.added) toast.success(`Added to KB! Total entries: ${result.total_entries}`);
      else toast.info('Already in knowledge base.');
    } catch { toast.error('Failed to add to KB'); }
  };

  const counts = {
    open:      tickets.filter(t => t.status === 'open').length,
    active:    tickets.filter(t => t.status === 'in_progress').length,
    escalated: tickets.filter(t => t.status === 'escalated').length,
    resolved:  tickets.filter(t => t.status === 'resolved').length,
    failed:    tickets.filter(t => t.status === 'failed').length,
    sla:       tickets.filter(isSlaWarning).length,
  };

  const ticket    = selectedTicket;
  const risk      = ticket?.riskAssessment;
  const riskLevel = ticket?.risk_level || risk?.risk_level || risk?.impact || 'low';

  return (
    <div className="min-h-screen bg-[#f5f5f7] flex flex-col">
      <div className="absolute inset-0 technical-grid pointer-events-none" />

      {/* ── Header ─────────────────────────────────────────── */}
      <header className="relative z-50 border-b border-black/[0.06] bg-white/90 backdrop-blur-xl sticky top-0 shadow-[0_1px_0_rgba(0,0,0,0.04)]">
        <div className="max-w-[1800px] mx-auto px-5 h-14 flex items-center justify-between gap-6">

          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/25">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-black tracking-tight text-slate-900 uppercase">Command Center</h1>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 uppercase">
                  Live
                </span>
              </div>
              <p className="text-[8px] font-mono text-slate-400 uppercase tracking-widest">NexusDesk Intelligence Platform</p>
            </div>
          </div>

          {/* Stats in header */}
          <div className="hidden md:flex items-center">
            <HeaderStat label="Open"      value={counts.open}      color="text-blue-600" />
            <HeaderStat label="Active"    value={counts.active}    color="text-amber-600" />
            <HeaderStat label="Escalated" value={counts.escalated} color="text-red-600" />
            <HeaderStat label="Resolved"  value={counts.resolved}  color="text-emerald-600" />
            {counts.sla > 0 && (
              <div className="ml-3 pl-3 border-l border-slate-200">
                <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-1 rounded-full bg-orange-50 text-orange-700 border border-orange-200 animate-pulse">
                  <Clock className="w-2.5 h-2.5" /> {counts.sla} SLA
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-bold text-slate-900">{profile?.displayName}</p>
              <p className="text-[8px] font-mono text-primary/80 uppercase tracking-wider">{profile?.role}</p>
            </div>
            <Button variant="ghost" size="icon-sm" onClick={signOut} className="text-slate-400 hover:text-red-500 hover:bg-red-50">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="relative flex-1 flex overflow-hidden max-w-[1800px] mx-auto w-full">

        {/* ── Sidebar nav ──────────────────────────────────── */}
        <aside className="w-14 border-r border-black/[0.06] bg-white/80 flex flex-col items-center py-5 gap-3 sticky top-14 h-[calc(100vh-3.5rem)]">
          {[
            { mode: 'tickets', Icon: LayoutDashboard },
            { mode: 'logs',    Icon: TerminalSquare },
          ].map(({ mode, Icon }) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                viewMode === mode
                  ? 'bg-indigo-50 text-primary shadow-sm'
                  : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'
              }`}
              title={mode.charAt(0).toUpperCase() + mode.slice(1)}
            >
              <Icon className="w-4 h-4" />
            </button>
          ))}
          <div className="mt-auto">
            <button
              onClick={signOut}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </aside>

        {viewMode === 'tickets' ? (
          <>
            {/* ── Ticket Queue ─────────────────────────────── */}
            <div className="w-80 border-r border-black/[0.06] bg-white/60 flex flex-col overflow-hidden sticky top-14 h-[calc(100vh-3.5rem)]">
              <div className="px-4 py-3 border-b border-black/[0.06] bg-white/80">
                <p className="text-[9px] font-mono uppercase tracking-widest text-slate-500">Ticket Queue</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">{tickets.length} Total</p>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                <AnimatePresence>
                  {tickets.map(t => (
                    <TicketCard
                      key={t._id || t.id}
                      ticket={t}
                      role="admin"
                      isSelected={(selectedTicket?._id || selectedTicket?.id) === (t._id || t.id)}
                      onClick={() => { setSelected(t); setActiveTab('ai_analysis'); }}
                    />
                  ))}
                </AnimatePresence>
                {tickets.length === 0 && (
                  <div className="py-16 text-center">
                    <Activity className="w-8 h-8 text-slate-200 mx-auto mb-2" />
                    <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">No tickets</p>
                  </div>
                )}
              </div>
            </div>

            {/* ── Detail panel ─────────────────────────────── */}
            <main className="flex-1 overflow-y-auto">
              {ticket ? (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={ticket._id || ticket.id}
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -8 }}
                    transition={{ duration: 0.25 }}
                    className="max-w-4xl mx-auto p-6 space-y-5"
                  >
                    {/* Ticket header */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[9px] font-mono text-slate-400 uppercase">
                            #{(ticket._id || ticket.id || '').slice(0, 8)}
                          </span>
                          <StatusBadge status={ticket.status} size="md" />
                          {ticket.category && (
                            <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-600 border border-indigo-200">
                              {ticket.category}
                            </span>
                          )}
                          {ticket.priority && (
                            <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 border border-slate-200">
                              {ticket.priority}
                            </span>
                          )}
                        </div>
                        <h2 className="text-xl font-black tracking-tight text-slate-900">{ticket.title}</h2>
                        <p className="text-xs text-slate-500">{ticket.userEmail}</p>
                      </div>

                      <div className="flex flex-col gap-2 shrink-0">
                        {['in_progress', 'resolving', 'open'].includes(ticket.status) && (
                          <Button
                            onClick={handleMarkResolved}
                            disabled={resolving === (ticket._id || ticket.id)}
                            className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 h-9 px-4"
                          >
                            <CheckCircle className="w-3.5 h-3.5 mr-2" />
                            Mark Resolved
                          </Button>
                        )}
                        {ticket.status === 'resolved' && ticket.resolution?.steps?.length > 0 && (
                          <Button
                            onClick={() => handleLearnFromTicket(ticket)}
                            variant="outline"
                            className="h-9 px-4 border-indigo-200 text-indigo-600 hover:bg-indigo-50"
                          >
                            <BookPlus className="w-3.5 h-3.5 mr-2" />
                            Learn from Ticket
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Risk + confidence summary */}
                    <RiskSummaryCard
                      risk={risk}
                      confidenceScore={ticket.confidence_score}
                      updatedAt={ticket.updatedAt}
                    />

                    {/* Alerts */}
                    {ticket.low_confidence && (
                      <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 flex items-center gap-3">
                        <AlertOctagon className="w-4 h-4 text-orange-600 shrink-0" />
                        <div>
                          <p className="text-xs font-bold text-orange-800">Low AI Confidence</p>
                          <p className="text-[10px] text-orange-700 mt-0.5">
                            Score below threshold — auto-escalated for human review. Verify before closing.
                          </p>
                        </div>
                      </div>
                    )}
                    {ticket.status === 'failed' && (
                      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 flex items-center gap-3">
                        <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                        <div>
                          <p className="text-xs font-bold text-rose-800">Pipeline Failed</p>
                          <p className="text-[10px] text-rose-700 mt-0.5">
                            AI pipeline failed after retries. Manual investigation required.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Sticky tabs */}
                    <div className="sticky-tabs-bar -mx-6 px-6 pt-1">
                      <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="w-full justify-start h-10 bg-transparent border-b border-slate-200/60 rounded-none gap-1 px-0">
                          {[
                            { value: 'ai_analysis',    label: 'AI Analysis',     dot: !!ticket.admin_response },
                            { value: 'employee_view',  label: 'Employee View',   dot: false },
                            { value: 'risk',           label: 'Risk',            dot: !!risk?.securityRisk },
                            { value: 'timeline',       label: 'Timeline',        dot: false },
                          ].map(tab => (
                            <TabsTrigger
                              key={tab.value}
                              value={tab.value}
                              className="relative text-xs data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none rounded-none pb-2 h-10"
                            >
                              {tab.label}
                              {tab.dot && (
                                <span className="ml-1.5 w-1.5 h-1.5 rounded-full bg-primary inline-block align-middle" />
                              )}
                            </TabsTrigger>
                          ))}
                        </TabsList>

                        <div className="pt-5">
                          <AnimatePresence mode="wait">
                            <TabsContent value="ai_analysis" className="mt-0" forceMount hidden={activeTab !== 'ai_analysis'}>
                              <motion.div key="ai" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
                                <AnalysisSection text={ticket.admin_response} riskLevel={riskLevel} />
                              </motion.div>
                            </TabsContent>

                            <TabsContent value="employee_view" className="mt-0" forceMount hidden={activeTab !== 'employee_view'}>
                              <motion.div key="emp" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
                                <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 shadow-sm">
                                  <div className="flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4 text-slate-400" />
                                    <p className="text-xs font-mono uppercase text-slate-500 tracking-wider">
                                      What the employee sees
                                    </p>
                                  </div>
                                  {ticket.employee_response ? (
                                    <div className="rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50/60 to-violet-50/30 p-4">
                                      <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-line">
                                        {ticket.employee_response}
                                      </p>
                                    </div>
                                  ) : (
                                    <p className="text-xs text-slate-400 font-mono uppercase tracking-wider text-center py-6">
                                      Pipeline still running…
                                    </p>
                                  )}
                                  {ticket.resolution?.automated && (
                                    <div className="flex items-center gap-1.5 pt-1">
                                      <Zap className="w-3 h-3 text-emerald-500" />
                                      <p className="text-[9px] font-mono text-emerald-600 uppercase tracking-wider">
                                        Auto-resolved by AI — no agent action required
                                      </p>
                                    </div>
                                  )}
                                  <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider pt-1 border-t border-slate-100">
                                    Admin fields (risk, analysis, confidence) hidden from this view
                                  </p>
                                </div>
                              </motion.div>
                            </TabsContent>

                            <TabsContent value="risk" className="mt-0" forceMount hidden={activeTab !== 'risk'}>
                              <motion.div key="risk" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
                                <RiskAssessmentPanel risk={risk} confidenceScore={ticket.confidence_score} />
                              </motion.div>
                            </TabsContent>

                            <TabsContent value="timeline" className="mt-0" forceMount hidden={activeTab !== 'timeline'}>
                              <motion.div key="tl" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
                                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                                  {(ticket.history || []).length > 0 ? (
                                    <div className="space-y-5 relative before:absolute before:left-[6px] before:top-3 before:bottom-3 before:w-px before:bg-gradient-to-b before:from-primary/30 before:to-transparent">
                                      {[...(ticket.history || [])].reverse().map((ev, i) => (
                                        <TimelineEvent key={i} event={ev} />
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-center text-[10px] font-mono text-slate-400 uppercase tracking-widest py-8">
                                      No timeline events yet
                                    </p>
                                  )}
                                </div>
                              </motion.div>
                            </TabsContent>
                          </AnimatePresence>
                        </div>
                      </Tabs>
                    </div>
                  </motion.div>
                </AnimatePresence>
              ) : (
                <div className="h-full flex flex-col items-center justify-center min-h-[60vh] text-center px-8">
                  <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-5 float">
                    <Activity className="w-8 h-8 text-slate-300" />
                  </div>
                  <h2 className="text-lg font-black text-slate-400 uppercase tracking-wide">Select a Ticket</h2>
                  <p className="font-mono text-[10px] uppercase tracking-widest text-slate-300 mt-2">
                    Choose from the queue to inspect
                  </p>
                </div>
              )}
            </main>
          </>
        ) : (
          /* ── Logs view ─────────────────────────────────────── */
          <main className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black text-slate-900 tracking-tight">System Logs</h2>
                <p className="text-sm text-slate-500 mt-1">Structured audit trail — every agent decision recorded</p>
              </div>
              <Button variant="outline" size="sm" onClick={fetchLogs}>Refresh</Button>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-2">
              {logs.length > 0 ? logs.map(log => (
                <motion.div
                  key={log._id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-xl bg-slate-50/70 border border-slate-100 space-y-1.5 hover:bg-slate-100/60 transition-colors"
                >
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-indigo-600 uppercase px-2 py-0.5 rounded-lg bg-indigo-50 border border-indigo-100">
                        {log.action}
                      </span>
                      {log.agent && log.agent !== 'system' && (
                        <span className="text-[10px] font-mono text-slate-500 uppercase px-2 py-0.5 rounded-lg bg-slate-100 border border-slate-200">
                          {log.agent}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      {new Date(log.timestamp).toLocaleString()}
                    </span>
                  </div>
                  {log.ticket_id && (
                    <p className="text-[9px] font-mono text-slate-400 uppercase">Ticket: {log.ticket_id.slice(0, 8)}</p>
                  )}
                  <p className="text-sm text-slate-700 leading-relaxed">{log.details}</p>
                </motion.div>
              )) : (
                <div className="text-center py-12 text-slate-400 font-mono text-[10px] uppercase tracking-widest">
                  No logs found
                </div>
              )}
            </div>
          </main>
        )}
      </div>
    </div>
  );
}
