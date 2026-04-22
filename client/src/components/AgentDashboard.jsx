import { useEffect, useState } from 'react';
import { useAuth } from './AuthGuard';
import { getTickets, updateTicket } from '../services/aiEngine';
import { TicketCard } from './TicketCard';
import { assessRisk, resolveTicket } from '../services/aiEngine';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  ShieldCheck, Cpu, AlertTriangle, CheckCircle, Activity,
  Users, LayoutDashboard, LogOut, Shield, Clock, ChevronRight,
  TrendingUp, Zap, Brain
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const riskColors = {
  low: { bg: 'bg-emerald-500/5', border: 'border-emerald-500/20', text: 'text-emerald-400', badge: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' },
  medium: { bg: 'bg-amber-500/5', border: 'border-amber-500/20', text: 'text-amber-400', badge: 'bg-amber-500/10 border-amber-500/20 text-amber-400' },
  high: { bg: 'bg-red-500/5', border: 'border-red-500/20', text: 'text-red-400', badge: 'bg-red-500/10 border-red-500/20 text-red-400' },
};

function MetricPill({ label, value, color }) {
  return (
    <div className="text-center px-4 border-r border-white/5 last:border-0">
      <p className="text-[8px] font-mono text-white/30 uppercase tracking-widest mb-0.5">{label}</p>
      <p className={`text-base font-black ${color}`}>{value}</p>
    </div>
  );
}

function TimelineEvent({ event }) {
  return (
    <div className="relative pl-7">
      <div className="absolute left-0 top-1 w-3.5 h-3.5 rounded-full bg-[#0d1117] border-2 border-primary z-10" />
      <p className="text-[9px] font-mono text-white/25">{new Date(event.timestamp).toLocaleTimeString()}</p>
      <p className="text-[10px] font-bold uppercase text-primary">{event.status?.replace('_', ' ')}</p>
      <p className="text-[10px] text-white/35 mt-0.5 leading-relaxed">{event.message}</p>
    </div>
  );
}

export function AgentDashboard() {
  const { profile, signOut } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [activeTab, setActiveTab] = useState('description');

  const fetchTickets = async () => {
    try {
      const data = await getTickets();
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

  useEffect(() => {
    fetchTickets();
    const interval = setInterval(fetchTickets, 5000);
    return () => clearInterval(interval);
  }, []);

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
    <div className="min-h-screen bg-[#070b14] flex flex-col">
      <div className="absolute inset-0 technical-grid opacity-20 pointer-events-none" />

      <header className="relative z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl sticky top-0">
        <div className="max-w-[1800px] mx-auto px-5 h-14 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3 shrink-0">
            <div className="relative">
              <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
                <Activity className="w-4 h-4 text-primary" />
              </div>
              <div className="absolute inset-0 rounded-lg bg-primary/20 blur-md -z-10" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-black tracking-tight text-white uppercase">Agentic Command</h1>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 uppercase tracking-wider">Operational</span>
              </div>
              <p className="text-[8px] font-mono text-white/25 uppercase tracking-widest">NexusDesk Intelligence Platform</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <MetricPill label="Open" value={counts.open} color="text-white/60" />
            <MetricPill label="Analyzing" value={counts.analyzing} color="text-primary" />
            <MetricPill label="Critical" value={counts.critical} color="text-red-400" />
            <MetricPill label="Resolved" value={counts.resolved} color="text-emerald-400" />
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <p className="text-xs font-bold text-white">{profile?.displayName}</p>
              <p className="text-[8px] font-mono text-primary/60 uppercase tracking-wider">Agent L3</p>
            </div>
            <Button variant="ghost" size="icon-sm" onClick={signOut} className="text-white/30 hover:text-red-400">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="relative flex-1 flex overflow-hidden max-w-[1800px] mx-auto w-full">
        <aside className="w-14 border-r border-white/5 bg-black/30 flex flex-col items-center py-5 gap-4 sticky top-14 h-[calc(100vh-3.5rem)]">
          <Button variant="ghost" size="icon-sm" className="text-primary bg-primary/10">
            <LayoutDashboard className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon-sm" className="text-white/20 hover:text-white">
            <Users className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon-sm" className="text-white/20 hover:text-white">
            <Shield className="w-4 h-4" />
          </Button>
          <div className="mt-auto">
            <Button variant="ghost" size="icon-sm" className="text-white/20 hover:text-red-400" onClick={signOut}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </aside>

        <div className="w-72 border-r border-white/5 flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5 bg-white/[0.01]">
            <p className="text-[9px] font-mono uppercase tracking-widest text-white/30">Active Queue</p>
            <p className="text-sm font-bold text-white mt-0.5">{tickets.length} Tickets</p>
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
                    <span className="text-[9px] font-mono text-white/25 uppercase">#{(selectedTicket._id || selectedTicket.id).slice(0, 8)}</span>
                    <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20">
                      {selectedTicket.category}
                    </span>
                    <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md bg-white/5 text-white/40 border border-white/5">
                      {selectedTicket.priority}
                    </span>
                  </div>
                  <h2 className="text-xl font-black tracking-tight text-white">{selectedTicket.title}</h2>
                </div>

                <Button
                  onClick={() => handleProcessTicket(selectedTicket)}
                  disabled={processing === (selectedTicket._id || selectedTicket.id) || selectedTicket.status === 'resolved'}
                  className="shrink-0 bg-primary hover:bg-primary/80 text-white font-bold shadow-lg shadow-primary/20 h-9 px-4"
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
                  <div className="rounded-xl border border-white/5 bg-white/[0.025] p-5">
                    <p className="text-sm text-white/70 leading-relaxed">{selectedTicket.description}</p>
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
                          <p className="text-[9px] font-mono uppercase text-primary/50">Detected Intent</p>
                          <p className="text-sm font-semibold text-white">{selectedTicket.analysis.intent}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-primary/50">Summary</p>
                          <p className="text-sm text-white/70">{selectedTicket.analysis.summary}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-primary/50">Suggested Priority</p>
                          <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-white/10 text-white/60 border border-white/10">
                            {selectedTicket.analysis.suggestedPriority}
                          </span>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-primary/50">Category</p>
                          <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-white/10 text-white/60 border border-white/10">
                            {selectedTicket.analysis.suggestedCategory}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-10 text-center">
                      <Brain className="w-8 h-8 text-white/10 mx-auto mb-3" />
                      <p className="text-[10px] font-mono text-white/20 uppercase tracking-wider">Run Agentic AI to see analysis</p>
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
                            <span className="text-emerald-400 font-mono text-xs shrink-0 pt-0.5">{String(i + 1).padStart(2, '0')}.</span>
                            <span className="text-white/70 leading-relaxed">{step}</span>
                          </li>
                        ))}
                      </ol>

                      {selectedTicket.resolution.result && (
                        <div className="pt-3 border-t border-emerald-500/10">
                          <p className="text-[9px] font-mono uppercase text-emerald-400/50 mb-1">Result</p>
                          <p className="text-xs text-white/50">{selectedTicket.resolution.result}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-10 text-center">
                      <CheckCircle className="w-8 h-8 text-white/10 mx-auto mb-3" />
                      <p className="text-[10px] font-mono text-white/20 uppercase tracking-wider">No resolution yet</p>
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
                              <span className="text-[9px] font-mono text-white/30 uppercase">Risk Score</span>
                              <div className="flex items-center gap-1.5">
                                <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${score > 0.7 ? 'bg-red-400' : score > 0.4 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                                    style={{ width: `${Math.round(score * 100)}%` }}
                                  />
                                </div>
                                <span className={`text-xs font-mono font-bold ${r.text}`}>{Math.round(score * 100)}%</span>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-lg bg-black/20 border border-white/5 p-3">
                            <p className="text-[9px] font-mono uppercase text-white/30 mb-1">Impact Level</p>
                            <span className={`text-xs font-mono uppercase font-bold ${r.text}`}>
                              {selectedTicket.riskAssessment.impact}
                            </span>
                          </div>
                          <div className="rounded-lg bg-black/20 border border-white/5 p-3">
                            <p className="text-[9px] font-mono uppercase text-white/30 mb-1">Security Risk</p>
                            <span className={`text-xs font-mono uppercase font-bold ${selectedTicket.riskAssessment.securityRisk ? 'text-red-400' : 'text-emerald-400'
                              }`}>
                              {selectedTicket.riskAssessment.securityRisk ? '⚠ Detected' : '✓ Clear'}
                            </span>
                          </div>
                          <div className="rounded-lg bg-black/20 border border-white/5 p-3">
                            <p className="text-[9px] font-mono uppercase text-white/30 mb-1">Compliance</p>
                            <span className={`text-xs font-mono uppercase font-bold ${selectedTicket.riskAssessment.complianceCheck ? 'text-emerald-400' : 'text-red-400'
                              }`}>
                              {selectedTicket.riskAssessment.complianceCheck ? '✓ Passed' : '✗ Failed'}
                            </span>
                          </div>
                        </div>

                        {selectedTicket.riskAssessment.notes && (
                          <div className="rounded-lg bg-black/20 border border-white/5 p-3">
                            <p className="text-[9px] font-mono uppercase text-white/30 mb-1.5">Risk Notes</p>
                            <p className="text-xs text-white/50 leading-relaxed">{selectedTicket.riskAssessment.notes}</p>
                          </div>
                        )}
                      </div>
                    );
                  })() : (
                    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-10 text-center">
                      <ShieldCheck className="w-8 h-8 text-white/10 mx-auto mb-3" />
                      <p className="text-[10px] font-mono text-white/20 uppercase tracking-wider">No risk assessment yet</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="timeline" className="mt-4">
                  <div className="rounded-xl border border-white/5 bg-white/[0.025] p-5">
                    <div className="space-y-5 relative before:absolute before:left-[6px] before:top-3 before:bottom-3 before:w-px before:bg-white/10">
                      {[...(selectedTicket.history || [])].reverse().map((event, i) => (
                        <TimelineEvent key={i} event={event} />
                      ))}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </motion.div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center min-h-[60vh]">
              <div className="opacity-10">
                <Activity className="w-16 h-16 mb-4 mx-auto" />
                <h2 className="text-xl font-black uppercase tracking-wide">Select a Ticket</h2>
                <p className="font-mono text-xs uppercase tracking-widest mt-2">Choose from the queue to inspect</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
