import { useEffect, useState } from 'react';
import { useAuth } from './AuthGuard';
import { getTickets, deleteTicket, submitFeedback, confirmPasswordReset } from '../services/aiEngine';
import { AIInputPanel } from './AIInputPanel';
import { TicketTimeline } from './TicketTimeline';
import { ShieldCheck, LogOut, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion } from 'motion/react';
import { toast } from 'sonner';

export function UserDashboard() {
  const { user, profile, signOut } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTickets = async () => {
    if (!user) return;
    try {
      const data = await getTickets(user.uid, 'user');
      setTickets(data);
    } catch {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    const iv = setInterval(fetchTickets, 8000);
    return () => clearInterval(iv);
  }, [user]);

  const handleDelete = async (ticketId) => {
    try {
      await deleteTicket(ticketId);
      toast.success('Ticket removed');
      fetchTickets();
    } catch {
      toast.error('Failed to delete ticket');
    }
  };

  const handleFeedback = async (ticketId, rating) => {
    try {
      await submitFeedback(ticketId, rating);
      toast.success(rating === 'positive' ? '👍 Thanks! This improves future AI accuracy.' : '👎 Feedback recorded — we\'ll improve this.');
      fetchTickets();
    } catch {
      toast.error('Failed to submit feedback');
    }
  };

  const handlePasswordConfirm = async (ticketId, { passwordResetMode, preferredPassword }) => {
    if (!user) return;
    try {
      await confirmPasswordReset(ticketId, {
        userId: user.uid,
        passwordResetMode,
        preferredPassword,
      });
      toast.success('Password reset complete — check your ticket for the new password.');
      fetchTickets();
    } catch (err) {
      toast.error(err.message?.includes('400') ? 'Enter a valid password (min 6 characters).' : 'Password reset failed');
    }
  };

  const stats = {
    total:     tickets.length,
    active:    tickets.filter(t => !['resolved', 'escalated', 'failed', 'linked', 'awaiting_password_confirm'].includes(t.status)).length,
    escalated: tickets.filter(t => t.status === 'escalated').length,
    resolved:  tickets.filter(t => t.status === 'resolved').length,
  };

  const firstName = profile?.displayName?.split(' ')[0] || 'there';

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <div className="absolute inset-0 technical-grid pointer-events-none" />

      <header className="sticky top-0 z-50 border-b border-black/[0.06] bg-white/80 backdrop-blur-xl shadow-[0_1px_0_rgba(0,0,0,0.04)]">
        <div className="max-w-7xl mx-auto px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/25">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-black tracking-tight text-slate-900">NexusDesk</h1>
              <p className="text-[9px] font-mono text-slate-400 uppercase tracking-widest leading-none">Enterprise AI-Native IT Operations</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] font-mono text-emerald-700 uppercase tracking-wider">Agentic AI Live</span>
            </div>
            <div className="hidden sm:block text-right">
              <p className="text-xs font-semibold text-slate-900">{profile?.displayName}</p>
              <p className="text-[9px] font-mono text-primary/80 uppercase tracking-wider">{profile?.role}</p>
            </div>
            <Button variant="ghost" size="icon-sm" onClick={signOut} className="text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="relative max-w-7xl mx-auto px-5 py-8">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="mb-8">
          <h2 className="text-2xl font-black tracking-tight text-slate-900">
            Good {getGreeting()},{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">{firstName}</span>
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">Your AI support team is online and monitoring your tickets automatically.</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.05 }} className="lg:col-span-4">
            <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.06)] backdrop-blur-sm lg:sticky lg:top-20">
              <AIInputPanel onTicketCreated={fetchTickets} stats={stats} />
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.1 }} className="lg:col-span-8">
            <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-5 shadow-[0_2px_16px_rgba(0,0,0,0.04)] min-h-[60vh]">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900 tracking-tight">Activity Feed</h3>
                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest mt-0.5">
                    {tickets.length} ticket{tickets.length !== 1 ? 's' : ''} · auto-refreshing
                  </p>
                </div>
              </div>
              <TicketTimeline
                tickets={tickets}
                onDelete={handleDelete}
                onFeedback={handleFeedback}
                onPasswordConfirm={handlePasswordConfirm}
                loading={loading}
              />
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}