import { useState } from 'react';
import { useAuth } from './AuthGuard';
import { createTicket } from '../services/aiEngine';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, Sparkles, Loader2, CheckCircle2, Brain, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const STEPS = [
  { id: 'create', label: 'Creating ticket', icon: Send },
  { id: 'analyze', label: 'NLP analysis', icon: Brain },
  { id: 'save', label: 'Saving results', icon: Cpu },
];

export function TicketForm({ onTicketCreated }) {
  const { user } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user || !title || !description) return;

    setLoading(true);
    setDone(false);
    const toastId = toast.loading('Submitting and analyzing ticket...');

    try {
      setStep('create');
      
      const ticketData = {
        title,
        description,
        userId: user.uid,
        userEmail: user.email,
      };

      setStep('analyze');
      
      await createTicket(ticketData);

      setStep('save');

      toast.success('Ticket submitted and analyzed!', { id: toastId });
      setDone(true);
      setTitle('');
      setDescription('');
      onTicketCreated?.();

      setTimeout(() => setDone(false), 3000);
    } catch (error) {
      toast.error('Failed to submit ticket', { id: toastId });
    } finally {
      setLoading(false);
      setStep(null);
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] backdrop-blur-xl overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-white/5">
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold text-white">New Support Request</h3>
        </div>
        <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
          Agentic AI · NLP Triage · Auto-Prioritize
        </p>
      </div>

      <div className="p-5">
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 rounded-lg border border-primary/20 bg-primary/5 p-3"
            >
              <div className="flex items-center gap-3">
                {STEPS.map((s, i) => {
                  const Icon = s.icon;
                  const isActive = step === s.id;
                  const isDone = STEPS.findIndex(x => x.id === step) > i;
                  return (
                    <div key={s.id} className="flex items-center gap-1.5">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center transition-all ${
                        isDone ? 'bg-emerald-500/20 text-emerald-400' :
                        isActive ? 'bg-primary/20 text-primary' :
                        'bg-white/5 text-white/20'
                      }`}>
                        {isDone ? <CheckCircle2 className="w-3 h-3" /> :
                         isActive ? <Loader2 className="w-3 h-3 animate-spin" /> :
                         <Icon className="w-3 h-3" />}
                      </div>
                      <span className={`text-[9px] font-mono uppercase ${
                        isDone ? 'text-emerald-400' : isActive ? 'text-primary' : 'text-white/20'
                      }`}>
                        {s.label}
                      </span>
                      {i < STEPS.length - 1 && (
                        <div className={`w-4 h-px mx-1 ${isDone ? 'bg-emerald-500/40' : 'bg-white/10'}`} />
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-mono uppercase text-white/40 tracking-wider">Subject</label>
            <Input
              placeholder="Brief summary of the issue"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-mono uppercase text-white/40 tracking-wider">Description</label>
              <span className="text-[9px] font-mono text-white/20">{description.length} chars</span>
            </div>
            <Textarea
              placeholder="Describe your problem in detail. Our AI agent will analyze it immediately using NLP."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-[110px]"
              disabled={loading}
              required
            />
          </div>

          <Button
            type="submit"
            disabled={loading || !title || !description}
            className="w-full h-11 bg-primary hover:bg-primary/90 text-white font-semibold shadow-lg shadow-primary/20 transition-all hover:scale-[1.01] active:scale-[0.99]"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : done ? (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4 text-emerald-300" />
                Submitted!
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Submit Ticket
              </>
            )}
          </Button>

          <p className="text-[9px] text-center text-white/20 font-mono uppercase tracking-wider">
            AI will auto-categorize · prioritize · assess risk
          </p>
        </form>
      </div>
    </div>
  );
}
