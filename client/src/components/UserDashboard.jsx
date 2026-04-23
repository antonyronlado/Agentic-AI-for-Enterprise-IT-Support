import { useEffect, useState } from 'react';
import { useAuth } from './AuthGuard';
import { getTickets, deleteTicket } from '../services/aiEngine';
import { TicketCard } from './TicketCard';
import { TicketForm } from './TicketForm';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ShieldCheck, LogOut, Ticket as TicketIcon, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'motion/react';
import { toast } from 'sonner';

function StatCard({ label, value, color, icon: Icon }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col gap-2 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{label}</p>
        <div className={`w-6 h-6 rounded-md flex items-center justify-center ${color.replace('text-', 'bg-').replace('400', '50')} ${color.replace('text-', 'text-').replace('400', '600')}`}>
          <Icon className={`w-3 h-3`} />
        </div>
      </div>
      <p className={`text-2xl font-black tracking-tight ${color.replace('text-', 'text-').replace('400', '600')}`}>{value}</p>
    </motion.div>
  );
}

export function UserDashboard() {
  const { user, profile, signOut } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTickets = async () => {
    if (!user) return;
    try {
      setLoading(true);
      const data = await getTickets(user.uid, profile?.role || "user");
      setTickets(data);
    } catch (error) {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [user]);

  const handleDelete = async (ticketId) => {
    try {
      await deleteTicket(ticketId);
      toast.success('Ticket deleted successfully');
      fetchTickets();
    } catch (error) {
      toast.error('Failed to delete ticket');
    }
  };

  const stats = {
    total: tickets.length,
    active: tickets.filter(t => t.status !== 'resolved').length,
    analyzing: tickets.filter(t => t.status === 'analyzing').length,
    resolved: tickets.filter(t => t.status === 'resolved').length,
    critical: tickets.filter(t => t.priority === 'critical').length,
  };

  const filterMap = {
    all: tickets,
    active: tickets.filter(t => t.status !== 'resolved'),
    resolved: tickets.filter(t => t.status === 'resolved'),
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="absolute inset-0 technical-grid opacity-[0.15] pointer-events-none" />

      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur-xl shadow-sm">
        <div className="max-w-7xl mx-auto px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-primary" />
              </div>
            </div>
            <div>
              <h1 className="text-sm font-black tracking-tight text-slate-900">NexusDesk</h1>
              <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest leading-none">User Portal</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] font-mono text-slate-400 uppercase tracking-wider">Live sync</span>
            </div>
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold text-slate-900">{profile?.displayName}</p>
              <p className="text-[9px] font-mono text-primary/80 uppercase">{profile?.role}</p>
            </div>
            <Button variant="ghost" size="icon-sm" onClick={signOut} className="text-slate-400 hover:text-red-500">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="relative max-w-7xl mx-auto px-5 py-8">
        <div className="mb-8">
          <h2 className="text-xl font-black text-slate-900 tracking-tight">
            Welcome back, <span className="text-primary">{profile?.displayName?.split(' ')[0]}</span>
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Your Agentic AI system is monitoring your tickets in real-time.
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <StatCard label="Total Tickets" value={stats.total} color="text-slate-700" icon={TicketIcon} />
          <StatCard label="Active" value={stats.active} color="text-blue-500" icon={TrendingUp} />
          <StatCard label="Critical" value={stats.critical} color="text-red-500" icon={AlertTriangle} />
          <StatCard label="Resolved" value={stats.resolved} color="text-emerald-500" icon={CheckCircle2} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-4">
            <TicketForm onTicketCreated={fetchTickets} />
          </div>

          <div className="lg:col-span-8">
            <Tabs defaultValue="all" className="w-full">
              <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                <TabsList className="h-8">
                  <TabsTrigger value="all">All ({stats.total})</TabsTrigger>
                  <TabsTrigger value="active">Active ({stats.active})</TabsTrigger>
                  <TabsTrigger value="resolved">Resolved ({stats.resolved})</TabsTrigger>
                </TabsList>
                <Button variant="outline" size="sm" onClick={fetchTickets}>
                  Refresh
                </Button>
              </div>

              {Object.entries(filterMap).map(([key, list]) => (
                <TabsContent key={key} value={key} className="mt-0">
                  <AnimatePresence mode="popLayout">
                    {list.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {list.map(ticket => (
                          <TicketCard 
                            key={ticket._id || ticket.id} 
                            ticket={ticket} 
                            onDelete={handleDelete}
                          />
                        ))}
                      </div>
                    ) : !loading ? (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="py-20 text-center rounded-xl border-2 border-dashed border-slate-200 bg-white"
                      >
                        <TicketIcon className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                        <p className="text-slate-400 font-mono text-[10px] uppercase tracking-widest">
                          No tickets in this view
                        </p>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </TabsContent>
              ))}
            </Tabs>
          </div>
        </div>
      </main>
    </div>
  );
}
