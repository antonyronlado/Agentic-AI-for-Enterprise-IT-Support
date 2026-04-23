import { useEffect, useState } from 'react';
import { useAuth } from './AuthGuard';
import { getTickets, updateTicket, getLogs } from '../services/aiEngine';
import { TicketCard } from './TicketCard';
import { assessRisk, resolveTicket } from '../services/aiEngine';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  ShieldCheck, Cpu, AlertTriangle, CheckCircle, Activity,
  Users, LayoutDashboard, LogOut, Shield, Clock, ChevronRight,
  TrendingUp, Zap, Brain, TerminalSquare
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const riskColors = {
  low: { bg: 'bg-emerald-50/50', border: 'border-emerald-100', text: 'text-emerald-600', badge: 'bg-emerald-100 border-emerald-200 text-emerald-700' },
  medium: { bg: 'bg-amber-50/50', border: 'border-amber-100', text: 'text-amber-600', badge: 'bg-amber-100 border-amber-200 text-amber-700' },
  high: { bg: 'bg-red-50/50', border: 'border-red-100', text: 'text-red-600', badge: 'bg-red-100 border-red-200 text-red-700' },
};



function TimelineEvent({ event }) {
  return (
    <div className="relative pl-7">
      <div className="absolute left-0 top-1 w-3.5 h-3.5 rounded-full bg-white border-2 border-primary z-10" />
      <p className="text-[9px] font-mono text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</p>
      <p className="text-[10px] font-bold uppercase text-primary">{event.status?.replace('_', ' ')}</p>
      <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{event.message}</p>
    </div>
  );
}

export function AgentDashboard() {
  const { profile, signOut } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [activeTab, setActiveTab] = useState('description');
  const [viewMode, setViewMode] = useState('tickets'); // 'tickets' or 'logs'
  const [logs, setLogs] = useState([]);

  const fetchTickets = async () => {
    if (viewMode !== 'tickets') return;
    try {
      const data = await getTickets(null, profile?.role || "admin");
      setTickets(data);
      if (selectedTicket) {
        const updated = data.find(t => (t._id || t.id) === (selectedTicket._id || selectedTicket.id));
        if (updated) setSelectedTicket(updated);
      }
    } catch (error) {
      console.error(error);
      toast.error('Failed to load tickets');
    }
  };

  const fetchLogsData = async () => {
    try {
      const data = await getLogs();
      setLogs(data);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load logs');
    }
  };

  useEffect(() => {
    if (viewMode === 'tickets') {
      fetchTickets();
      const interval = setInterval(fetchTickets, 5000);
      return () => clearInterval(interval);
    } else if (viewMode === 'logs') {
      fetchLogsData();
      const interval = setInterval(fetchLogsData, 5000);
      return () => clearInterval(interval);
    }
  }, [viewMode]);

  const handleProcessTicket = async (ticket) => {
    const tId = ticket._id || ticket.id;
    setProcessing(tId);
    const toastId = toast.loading(`Agentic AI processing #${tId.slice(0, 8)}...`);

    try {
      toast.loading('Risk assessment running...', { id: toastId });
      const risk = await assessRisk(ticket);

      toast.loading('Generating resolution path...', { id: toastId });
      const resolution = await resolveTicket({ ...ticket, riskAssessment: risk });

      const nextStatus = resolution.automated ? 'resolved' : 'resolving';

      await updateTicket(tId, {
        status: nextStatus,
        riskAssessment: risk,
        resolution,
        updatedAt: Date.now(),
        history: [...(ticket.history || []), {
          timestamp: Date.now(),
          status: nextStatus,
          message: `Agentic AI: ${resolution.automated ? 'Automatically resolved' : 'Resolution path proposed'}. Risk impact: ${risk.impact}. Score: ${risk.riskScore ?? 'N/A'}`
        }]
      });

      toast.success(resolution.automated ? 'Ticket auto-resolved!' : 'Resolution path proposed.', { id: toastId });
      fetchTickets();
    } catch (error) {
      console.error(error);
      toast.error('AI processing failed', { id: toastId });
    } finally {
      setProcessing(null);
    }
  };

  const counts = {
    open: tickets.filter(t => t.status === 'open').length,
    analyzing: tickets.filter(t => t.status === 'analyzing').length,
    critical: tickets.filter(t => t.priority === 'critical').length,
    resolved: tickets.filter(t => t.status === 'resolved').length,
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <div className="absolute inset-0 technical-grid opacity-[0.15] pointer-events-none" />

      <header className="relative z-50 border-b border-slate-200 bg-white/80 backdrop-blur-xl sticky top-0 shadow-sm">
        <div className="max-w-[1800px] mx-auto px-5 h-14 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3 shrink-0">
            <div className="relative">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center">
                <Activity className="w-4 h-4 text-primary" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-black tracking-tight text-slate-900 uppercase">Agentic Command</h1>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 border border-indigo-200 uppercase tracking-wider">Operational</span>
              </div>
              <p className="text-[8px] font-mono text-slate-500 uppercase tracking-widest">NexusDesk Intelligence Platform</p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <p className="text-xs font-bold text-slate-900">{profile?.displayName}</p>
              <p className="text-[8px] font-mono text-primary/80 uppercase tracking-wider">Agent L3</p>
            </div>
            <Button variant="ghost" size="icon-sm" onClick={signOut} className="text-slate-400 hover:text-red-500">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="relative flex-1 flex overflow-hidden max-w-[1800px] mx-auto w-full">
        <aside className="w-14 border-r border-slate-200 bg-white flex flex-col items-center py-5 gap-4 sticky top-14 h-[calc(100vh-3.5rem)]">
          <Button 
            variant="ghost" 
            size="icon-sm" 
            className={viewMode === 'tickets' ? "text-primary bg-indigo-50" : "text-slate-400 hover:text-slate-900"}
            onClick={() => setViewMode('tickets')}
          >
            <LayoutDashboard className="w-4 h-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon-sm" 
            className={viewMode === 'logs' ? "text-primary bg-indigo-50" : "text-slate-400 hover:text-slate-900"}
            onClick={() => setViewMode('logs')}
          >
            <TerminalSquare className="w-4 h-4" />
          </Button>
          <div className="mt-auto">
            <Button variant="ghost" size="icon-sm" className="text-slate-400 hover:text-red-500" onClick={signOut}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </aside>

        {viewMode === 'tickets' ? (
        <>
        <div className="w-72 border-r border-slate-200 bg-white flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
            <p className="text-[9px] font-mono uppercase tracking-widest text-slate-500">Active Queue</p>
            <p className="text-sm font-bold text-slate-900 mt-0.5">{tickets.length} Tickets</p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <AnimatePresence>
              {tickets.map(ticket => (
                <TicketCard
                  key={ticket._id || ticket.id}
                  ticket={ticket}
                  onClick={() => { setSelectedTicket(ticket); setActiveTab('description'); }}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>

        <main className="flex-1 overflow-y-auto p-6">
          {selectedTicket ? (
            <motion.div
              key={selectedTicket._id || selectedTicket.id}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
              className="max-w-4xl mx-auto space-y-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[9px] font-mono text-slate-400 uppercase">#{(selectedTicket._id || selectedTicket.id).slice(0, 8)}</span>
                    <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-600 border border-indigo-200">
                      {selectedTicket.category}
                    </span>
                    <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 border border-slate-200">
                      {selectedTicket.priority}
                    </span>
                  </div>
                  <h2 className="text-xl font-black tracking-tight text-slate-900">{selectedTicket.title}</h2>
                </div>

                <div className="flex gap-2 shrink-0">
                  {selectedTicket.status === 'resolving' && (
                    <Button
                      onClick={async () => {
                        const tId = selectedTicket._id || selectedTicket.id;
                        setProcessing(tId);
                        try {
                          await updateTicket(tId, { 
                            status: 'resolved',
                            updatedAt: Date.now(),
                            history: [...(selectedTicket.history || []), {
                              timestamp: Date.now(),
                              status: 'resolved',
                              message: 'Agent manually verified and resolved the ticket.'
                            }]
                          });
                          toast.success("Ticket successfully marked as resolved!");
                          fetchTickets();
                        } catch (error) {
                          toast.error("Failed to resolve ticket");
                        } finally {
                          setProcessing(null);
                        }
                      }}
                      disabled={processing === (selectedTicket._id || selectedTicket.id)}
                      className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 h-9 px-4"
                    >
                      <CheckCircle className="w-3.5 h-3.5 mr-2" />
                      Mark as Resolved
                    </Button>
                  )}
                  <Button
                    onClick={() => handleProcessTicket(selectedTicket)}
                    disabled={processing === (selectedTicket._id || selectedTicket.id) || selectedTicket.status === 'resolved'}
                    className="bg-primary hover:bg-primary/80 text-white font-bold shadow-lg shadow-primary/20 h-9 px-4"
                  >
                    {processing === (selectedTicket._id || selectedTicket.id) ? (
                      <>
                        <Activity className="w-3.5 h-3.5 animate-spin mr-2" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Cpu className="w-3.5 h-3.5 mr-2" />
                        Run Agentic AI
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                  <TabsTrigger value="description">Description</TabsTrigger>
                  <TabsTrigger value="analysis">
                    AI Analysis
                    {selectedTicket.analysis && <span className="ml-1 w-1 h-1 rounded-full bg-primary inline-block" />}
                  </TabsTrigger>
                  <TabsTrigger value="resolution">
                    Resolution
                    {selectedTicket.resolution && <span className="ml-1 w-1 h-1 rounded-full bg-emerald-400 inline-block" />}
                  </TabsTrigger>
                  <TabsTrigger value="risk">
                    Risk
                    {selectedTicket.riskAssessment?.securityRisk && <span className="ml-1 w-1 h-1 rounded-full bg-red-400 inline-block" />}
                  </TabsTrigger>
                  <TabsTrigger value="timeline">Timeline</TabsTrigger>
                </TabsList>

                <TabsContent value="description" className="mt-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <p className="text-sm text-slate-700 leading-relaxed">{selectedTicket.description}</p>
                  </div>
                </TabsContent>

                <TabsContent value="analysis" className="mt-4">
                  {selectedTicket.analysis ? (
                    <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Brain className="w-4 h-4 text-primary" />
                          <span className="text-xs font-mono uppercase text-primary tracking-wider">NLP Analysis Result</span>
                        </div>
                        {selectedTicket.analysis.confidenceScore !== undefined && (
                          <div className="flex items-center gap-2">
                            <span className="text-[9px] font-mono text-white/30 uppercase">Confidence</span>
                            <div className="flex items-center gap-1.5">
                              <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-primary"
                                  style={{ width: `${Math.round(selectedTicket.analysis.confidenceScore * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono text-primary font-bold">
                                {Math.round(selectedTicket.analysis.confidenceScore * 100)}%
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-indigo-400">Detected Intent</p>
                          <p className="text-sm font-semibold text-indigo-900">{selectedTicket.analysis.intent}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-indigo-400">Summary</p>
                          <p className="text-sm text-indigo-700">{selectedTicket.analysis.summary}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-indigo-400">Suggested Priority</p>
                          <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-white/50 text-indigo-600 border border-indigo-100">
                            {selectedTicket.analysis.suggestedPriority}
                          </span>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-indigo-400">Category</p>
                          <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-white/50 text-indigo-600 border border-indigo-100">
                            {selectedTicket.analysis.suggestedCategory}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
                      <Brain className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                      <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Run Agentic AI to see analysis</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="resolution" className="mt-4">
                  {selectedTicket.resolution ? (
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                          <span className="text-xs font-mono uppercase text-emerald-400 tracking-wider">Resolution Path</span>
                        </div>
                        <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded-md border ${selectedTicket.resolution.automated
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          }`}>
                          {selectedTicket.resolution.automated ? '⚡ Auto-Resolved' : '👤 Escalated'}
                        </span>
                      </div>

                      {selectedTicket.resolution.escalationReason && (
                        <div className="rounded-lg bg-amber-500/5 border border-amber-500/10 px-3 py-2">
                          <p className="text-[9px] font-mono uppercase text-amber-400/60 mb-1">Escalation Reason</p>
                          <p className="text-xs text-amber-300/70">{selectedTicket.resolution.escalationReason}</p>
                        </div>
                      )}

                      <ol className="space-y-2">
                        {selectedTicket.resolution.steps?.map((step, i) => (
                          <li key={i} className="flex gap-3 text-sm">
                            <span className="text-emerald-500 font-mono text-xs shrink-0 pt-0.5">{String(i + 1).padStart(2, '0')}.</span>
                            <span className="text-emerald-800 leading-relaxed">{step}</span>
                          </li>
                        ))}
                      </ol>

                      {selectedTicket.resolution.result && (
                        <div className="pt-3 border-t border-emerald-500/10">
                          <p className="text-[9px] font-mono uppercase text-emerald-600/50 mb-1">Result</p>
                          <p className="text-xs text-emerald-800/70">{selectedTicket.resolution.result}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
                      <CheckCircle className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                      <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">No resolution yet</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="risk" className="mt-4">
                  {selectedTicket.riskAssessment ? (() => {
                    const r = riskColors[selectedTicket.riskAssessment.impact] || riskColors.low;
                    const score = selectedTicket.riskAssessment.riskScore;
                    return (
                      <div className={`rounded-xl border p-5 space-y-4 ${r.bg} ${r.border}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <ShieldCheck className={`w-4 h-4 ${r.text}`} />
                            <span className={`text-xs font-mono uppercase tracking-wider ${r.text}`}>Risk Assessment</span>
                          </div>
                          {score !== undefined && (
                            <div className="flex items-center gap-2">
                              <span className="text-[9px] font-mono text-slate-500 uppercase">Risk Score</span>
                              <div className="flex items-center gap-1.5">
                                <div className="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${score > 0.7 ? 'bg-red-500' : score > 0.4 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                    style={{ width: `${Math.round(score * 100)}%` }}
                                  />
                                </div>
                                <span className={`text-xs font-mono font-bold ${r.text}`}>{Math.round(score * 100)}%</span>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                            <p className="text-[9px] font-mono uppercase text-slate-500 mb-1">Impact Level</p>
                            <span className={`text-xs font-mono uppercase font-bold ${r.text}`}>
                              {selectedTicket.riskAssessment.impact}
                            </span>
                          </div>
                          <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                            <p className="text-[9px] font-mono uppercase text-slate-500 mb-1">Security Risk</p>
                            <span className={`text-xs font-mono uppercase font-bold ${selectedTicket.riskAssessment.securityRisk ? 'text-red-600' : 'text-emerald-600'
                              }`}>
                              {selectedTicket.riskAssessment.securityRisk ? '⚠ Detected' : '✓ Clear'}
                            </span>
                          </div>
                          <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                            <p className="text-[9px] font-mono uppercase text-slate-500 mb-1">Compliance</p>
                            <span className={`text-xs font-mono uppercase font-bold ${selectedTicket.riskAssessment.complianceCheck ? 'text-emerald-600' : 'text-red-600'
                              }`}>
                              {selectedTicket.riskAssessment.complianceCheck ? '✓ Passed' : '✗ Failed'}
                            </span>
                          </div>
                        </div>

                        {selectedTicket.riskAssessment.notes && (
                          <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                            <p className="text-[9px] font-mono uppercase text-slate-500 mb-1.5">Risk Notes</p>
                            <p className="text-xs text-slate-600 leading-relaxed">{selectedTicket.riskAssessment.notes}</p>
                          </div>
                        )}
                      </div>
                    );
                  })() : (
                    <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
                      <ShieldCheck className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                      <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">No risk assessment yet</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="timeline" className="mt-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="space-y-5 relative before:absolute before:left-[6px] before:top-3 before:bottom-3 before:w-px before:bg-slate-200">
                      {[...(selectedTicket.history || [])].reverse().map((event, i) => (
                        <TimelineEvent key={i} event={event} />
                      ))}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </motion.div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center min-h-[60vh] text-slate-300">
              <div>
                <Activity className="w-16 h-16 mb-4 mx-auto" />
                <h2 className="text-xl font-black uppercase tracking-wide">Select a Ticket</h2>
                <p className="font-mono text-xs uppercase tracking-widest mt-2">Choose from the queue to inspect</p>
              </div>
            </div>
          )}
        </main>
        </>
        ) : (
          <main className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black text-slate-900 tracking-tight">System Logs</h2>
                <p className="text-sm text-slate-500 mt-1">Real-time audit trail of actions</p>
              </div>
              <Button variant="outline" size="sm" onClick={fetchLogsData}>Refresh Logs</Button>
            </div>
            
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="space-y-4">
                {logs.length > 0 ? logs.map(log => (
                  <div key={log._id || log.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-[10px] font-mono text-indigo-600 uppercase px-2 py-0.5 rounded bg-indigo-50 border border-indigo-100">
                        {log.action}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-slate-700">{log.details}</p>
                  </div>
                )) : (
                  <div className="text-center py-10 text-slate-400 font-mono text-[10px] uppercase tracking-widest">
                    No logs found
                  </div>
                )}
              </div>
            </div>
          </main>
        )}
      </div>
    </div>
  );
}
