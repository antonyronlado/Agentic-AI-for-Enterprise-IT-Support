import { createContext, useContext, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Shield, LogIn, Cpu, Zap, UserPlus, AlertCircle } from 'lucide-react';
import { motion } from 'motion/react';
import { login, register, getMe, setToken } from '../services/aiEngine';
import { toast } from 'sonner';

const AuthContext = createContext({
  user:    null,
  profile: null,
  loading: true,
  isAdmin: false,
  isAgent: false,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const [isRegistering, setIsRegistering] = useState(false);
  const [username,      setUsername]      = useState('');
  const [password,      setPassword]      = useState('');
  const [email,         setEmail]         = useState('');
  const [authLoading,   setAuthLoading]   = useState(false);
  const [authError,     setAuthError]     = useState('');

  // ── Session restore — ALWAYS validate token server-side ──────────────
  useEffect(() => {
    const restore = async () => {
      const storedToken = localStorage.getItem('nexus_token');
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Calls GET /auth/me with the stored token — gets fresh role from DB
        const freshProfile = await getMe();
        const userData = {
          uid:         freshProfile.uid,
          email:       freshProfile.email,
          displayName: freshProfile.username,
          role:        freshProfile.role,   // role comes from server, never localStorage
        };
        setUser(userData);
        setProfile(userData);
      } catch {
        // Token invalid or expired — clear everything and force re-login
        localStorage.removeItem('nexus_token');
        localStorage.removeItem('nexus_user');
        setToken(null);
      } finally {
        setLoading(false);
      }
    };
    restore();
  }, []);

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      let data;
      if (isRegistering) {
        data = await register(username, email, password);
        toast.success('Registration successful! Logging in...');
      } else {
        data = await login(username, password);
        toast.success('Login successful!');
      }

      // Store the auth token — role is NOT stored in localStorage
      setToken(data.auth_token);

      const userData = {
        uid:         data.uid,
        email:       data.email,
        displayName: data.username,
        role:        data.role,   // from server response only
      };

      setUser(userData);
      setProfile(userData);
    } catch (err) {
      const msg = err.message || 'Authentication failed. Please try again.';
      setAuthError(msg);
      toast.error(msg);
    } finally {
      setAuthLoading(false);
    }
  };

  const signOut = () => {
    localStorage.removeItem('nexus_token');
    localStorage.removeItem('nexus_user');  // clean up any legacy data
    setToken(null);
    setUser(null);
    setProfile(null);
    setUsername('');
    setPassword('');
    setEmail('');
    setAuthError('');
  };

  const value = {
    user,
    profile,
    loading,
    isAdmin: profile?.role === 'admin',
    isAgent: profile?.role === 'agent' || profile?.role === 'admin',
    signOut,
  };

  // ── Loading splash ────────────────────────────────────────────────────
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
            <p className="text-xs font-mono text-primary/80 uppercase tracking-widest">Verifying Session...</p>
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

  // ── Login / Register form ─────────────────────────────────────────────
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
                  autoComplete="username"
                  maxLength={100}
                />
                {isRegistering && (
                  <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
                    required
                    autoComplete="email"
                    maxLength={200}
                  />
                )}
                <input
                  type="password"
                  placeholder={isRegistering ? 'Password (min 8 characters)' : 'Password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
                  required
                  autoComplete={isRegistering ? 'new-password' : 'current-password'}
                  minLength={isRegistering ? 8 : undefined}
                />

                {/* Inline error display */}
                {authError && (
                  <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                    <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                    <p className="text-xs text-red-700">{authError}</p>
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={authLoading}
                  className="w-full h-12 text-sm font-semibold bg-primary hover:bg-primary/90 text-white transition-all hover:scale-[1.02] active:scale-[0.98] shadow-md shadow-primary/20"
                >
                  {isRegistering ? <UserPlus className="mr-2 h-4 w-4" /> : <LogIn className="mr-2 h-4 w-4" />}
                  {authLoading ? 'Processing...' : (isRegistering ? 'Register' : 'Sign In')}
                </Button>

                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => { setIsRegistering(!isRegistering); setAuthError(''); }}
                    className="text-xs text-primary/80 hover:text-primary transition-colors"
                  >
                    {isRegistering ? 'Already have an account? Sign In' : 'Need an account? Register'}
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
