import { createContext, useContext, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Shield, LogIn, Cpu, Zap } from 'lucide-react';
import { motion } from 'motion/react';

const AuthContext = createContext({
  user: null,
  profile: null,
  loading: true,
  isAdmin: false,
  isAgent: false,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('nexus_user');
    if (savedUser) {
      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      setProfile({
        uid: parsedUser.uid,
        email: parsedUser.email,
        displayName: parsedUser.displayName,
        role: parsedUser.role,
      });
    }
    setLoading(false);
  }, []);

  const signInWithMock = () => {
    const mockUser = {
      uid: 'mock-user-123',
      email: 'user@nexusdesk.local',
      displayName: 'Local User',
      role: 'user',
    };
    localStorage.setItem('nexus_user', JSON.stringify(mockUser));
    setUser(mockUser);
    setProfile(mockUser);
  };

  const signOut = () => {
    localStorage.removeItem('nexus_user');
    setUser(null);
    setProfile(null);
  };

  const value = {
    user,
    profile,
    loading,
    isAdmin: profile?.role === 'admin',
    isAgent: profile?.role === 'agent' || profile?.role === 'admin',
    signOut,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#070b14]">
        <div className="flex flex-col items-center gap-5">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center">
              <Cpu className="w-8 h-8 text-primary animate-pulse" />
            </div>
            <div className="absolute inset-0 rounded-2xl bg-primary/20 blur-xl animate-pulse" />
          </div>
          <div className="space-y-1 text-center">
            <p className="text-sm font-mono text-white/60 uppercase tracking-[0.2em]">Initializing</p>
            <p className="text-xs font-mono text-primary/60 uppercase tracking-widest">Secure Session...</p>
          </div>
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#070b14] overflow-hidden relative">
        <div className="absolute inset-0">
          <div className="absolute inset-0 technical-grid opacity-40" />
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-cyan-500/5 rounded-full blur-[80px]" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="relative z-10 w-full max-w-md mx-4"
        >
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-8 shadow-2xl">
            <div className="text-center mb-8">
              <div className="inline-flex mb-5 relative">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <Shield className="w-8 h-8 text-primary" />
                </div>
                <div className="absolute inset-0 rounded-2xl bg-primary/20 blur-2xl -z-10" />
              </div>

              <div className="flex items-center justify-center gap-2 mb-2">
                <Zap className="w-3 h-3 text-primary" />
                <span className="text-[10px] font-mono text-primary uppercase tracking-[0.3em]">Agentic AI System</span>
                <Zap className="w-3 h-3 text-primary" />
              </div>

              <h1 className="text-3xl font-black tracking-tight text-white mb-1">NexusDesk</h1>
              <p className="text-sm text-white/40 font-mono uppercase tracking-wider">IT Service Intelligence Platform</p>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3 mb-6">
                {[
                  { label: 'NLP Triage', icon: '🧠' },
                  { label: 'RAG Search', icon: '🔍' },
                  { label: 'Risk Guard', icon: '🛡️' },
                ].map((feat) => (
                  <div key={feat.label} className="rounded-lg border border-white/5 bg-white/[0.02] p-3 text-center">
                    <div className="text-lg mb-1">{feat.icon}</div>
                    <p className="text-[9px] font-mono text-white/40 uppercase tracking-wider">{feat.label}</p>
                  </div>
                ))}
              </div>

              <Button
                onClick={signInWithMock}
                className="w-full h-12 text-sm font-semibold bg-primary hover:bg-primary/90 text-white transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-primary/20"
              >
                <LogIn className="mr-2 h-4 w-4" />
                Sign in (Local Session)
              </Button>

              <p className="text-center text-[10px] text-white/20 font-mono uppercase tracking-widest">
                Secure Access Only • Authorized Personnel
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
