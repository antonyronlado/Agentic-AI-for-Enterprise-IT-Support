import { createContext, useContext, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Shield, LogIn, Cpu, Zap, UserPlus } from 'lucide-react';
import { motion } from 'motion/react';
import { login, register } from '../services/aiEngine';
import { toast } from 'sonner';

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
  
  // Auth Form State
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

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

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      let data;
      if (isRegistering) {
        data = await register(username, email, password);
        toast.success("Registration successful! Logging in...");
      } else {
        data = await login(username, password);
        toast.success("Login successful!");
      }
      
      const userData = {
        uid: data.uid,
        email: data.email,
        displayName: data.username,
        role: data.role,
      };
      
      localStorage.setItem('nexus_user', JSON.stringify(userData));
      setUser(userData);
      setProfile(userData);
    } catch (err) {
      toast.error(err.message || "Authentication failed");
    } finally {
      setAuthLoading(false);
    }
  };

  const signOut = () => {
    localStorage.removeItem('nexus_user');
    setUser(null);
    setProfile(null);
    setUsername('');
    setPassword('');
    setEmail('');
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
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-5">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
              <Cpu className="w-8 h-8 text-primary animate-pulse" />
            </div>
            <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-xl animate-pulse" />
          </div>
          <div className="space-y-1 text-center">
            <p className="text-sm font-mono text-slate-500 uppercase tracking-[0.2em]">Initializing</p>
            <p className="text-xs font-mono text-primary/80 uppercase tracking-widest">Secure Session...</p>
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
      <div className="min-h-screen flex items-center justify-center bg-slate-50 overflow-hidden relative">
        <div className="absolute inset-0">
          <div className="absolute inset-0 technical-grid opacity-[0.15]" />
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-cyan-500/10 rounded-full blur-[80px]" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="relative z-10 w-full max-w-md mx-4"
        >
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/50">
            <div className="text-center mb-8">
              <div className="inline-flex mb-5 relative">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Shield className="w-8 h-8 text-primary" />
                </div>
                <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-2xl -z-10" />
              </div>

              <div className="flex items-center justify-center gap-2 mb-2">
                <Zap className="w-3 h-3 text-primary" />
                <span className="text-[10px] font-mono text-primary uppercase tracking-[0.3em]">Agentic AI System</span>
                <Zap className="w-3 h-3 text-primary" />
              </div>

              <h1 className="text-3xl font-black tracking-tight text-slate-900 mb-1">NexusDesk</h1>
              <p className="text-sm text-slate-500 font-mono uppercase tracking-wider">IT Service Intelligence Platform</p>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3 mb-6">
                {[
                  { label: 'NLP Triage', icon: '🧠' },
                  { label: 'RAG Search', icon: '🔍' },
                  { label: 'Risk Guard', icon: '🛡️' },
                ].map((feat) => (
                  <div key={feat.label} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-center">
                    <div className="text-lg mb-1">{feat.icon}</div>
                    <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{feat.label}</p>
                  </div>
                ))}
              </div>

              <form onSubmit={handleAuth} className="space-y-4">
                <input
                  type="text"
                  placeholder="Username or Email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
                  required
                />
                {isRegistering && (
                  <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
                    required
                  />
                )}
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
                  required
                />

                <Button
                  type="submit"
                  disabled={authLoading}
                  className="w-full h-12 text-sm font-semibold bg-primary hover:bg-primary/90 text-white transition-all hover:scale-[1.02] active:scale-[0.98] shadow-md shadow-primary/20"
                >
                  {isRegistering ? <UserPlus className="mr-2 h-4 w-4" /> : <LogIn className="mr-2 h-4 w-4" />}
                  {authLoading ? "Processing..." : (isRegistering ? "Register" : "Sign In")}
                </Button>
                
                <div className="text-center">
                  <button 
                    type="button" 
                    onClick={() => setIsRegistering(!isRegistering)}
                    className="text-xs text-primary/80 hover:text-primary transition-colors"
                  >
                    {isRegistering ? "Already have an account? Sign In" : "Need an account? Register"}
                  </button>
                </div>
              </form>

              <p className="text-center text-[10px] text-slate-400 font-mono uppercase tracking-widest mt-4">
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
