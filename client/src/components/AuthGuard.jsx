import { createContext, useContext, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Shield, LogIn, Cpu, Zap, UserPlus, AlertCircle, ArrowLeft, Mail, Lock, KeyRound } from 'lucide-react';
import { motion } from 'motion/react';
import { login, register, getMe, setToken, requestPasswordResetOTP, verifyOTP, resetPassword } from '../services/aiEngine';
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

  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotOTP, setForgotOTP] = useState('');
  const [forgotNewPassword, setForgotNewPassword] = useState('');
  const [forgotStep, setForgotStep] = useState(1);
  const [forgotLoading, setForgotLoading] = useState(false);

  useEffect(() => {
    const restore = async () => {
      const storedToken = localStorage.getItem('nexus_token');
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        const freshProfile = await getMe();
        const userData = {
          uid:         freshProfile.uid,
          email:       freshProfile.email,
          displayName: freshProfile.username,
          role:        freshProfile.role,
        };
        // Cache profile so we can restore it offline
        localStorage.setItem('nexus_user', JSON.stringify(userData));
        setUser(userData);
        setProfile(userData);
      } catch (err) {
        const isNetworkError =
          err instanceof TypeError ||
          (err.message && (
            err.message.includes('Failed to fetch') ||
            err.message.includes('NetworkError') ||
            err.message.includes('ERR_CONNECTION_REFUSED')
          ));

        if (isNetworkError) {
          // Backend is temporarily down — restore from cache so user stays logged in
          const cached = localStorage.getItem('nexus_user');
          if (cached) {
            try {
              const userData = JSON.parse(cached);
              setUser(userData);
              setProfile(userData);
            } catch {
              // corrupted cache — clear and show login
              localStorage.removeItem('nexus_token');
              localStorage.removeItem('nexus_user');
              setToken(null);
            }
          } else {
            // No cache — show login but keep token so retry works
            setUser(null);
          }
        } else {
          // 401 or other auth error — token is invalid, clear everything
          localStorage.removeItem('nexus_token');
          localStorage.removeItem('nexus_user');
          setToken(null);
        }
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

      setToken(data.auth_token);

      const userData = {
        uid:         data.uid,
        email:       data.email,
        displayName: data.username,
        role:        data.role,
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

  const handleRequestOTP = async (e) => {
    e.preventDefault();
    setForgotLoading(true);
    try {
      await requestPasswordResetOTP(forgotEmail);
      toast.success('OTP sent to your email!');
      setForgotStep(2);
    } catch (err) {
      toast.error(err.message || 'Failed to send OTP');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setForgotLoading(true);
    try {
      await verifyOTP(forgotEmail, forgotOTP);
      toast.success('OTP verified! Enter new password.');
      setForgotStep(3);
    } catch (err) {
      toast.error(err.message || 'Invalid OTP');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setForgotLoading(true);
    try {
      await resetPassword(forgotEmail, forgotNewPassword);
      toast.success('Password reset successfully! Please login.');
      setShowForgotPassword(false);
      setForgotStep(1);
      setForgotEmail('');
      setForgotOTP('');
      setForgotNewPassword('');
    } catch (err) {
      toast.error(err.message || 'Failed to reset password');
    } finally {
      setForgotLoading(false);
    }
  };

  const signOut = () => {
    localStorage.removeItem('nexus_token');
    localStorage.removeItem('nexus_user');
    setToken(null);
    setUser(null);
    setProfile(null);
    setUsername('');
    setPassword('');
    setEmail('');
    setAuthError('');
    setShowForgotPassword(false);
    setForgotStep(1);
    setForgotEmail('');
    setForgotOTP('');
    setForgotNewPassword('');
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

                {}
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

                <div className="text-center flex justify-between items-center">
                  <button
                    type="button"
                    onClick={() => { setIsRegistering(!isRegistering); setAuthError(''); }}
                    className="text-xs text-primary/80 hover:text-primary transition-colors"
                  >
                    {isRegistering ? 'Already have an account? Sign In' : 'Need an account? Register'}
                  </button>
                  {!isRegistering && (
                    <button
                      type="button"
                      onClick={() => setShowForgotPassword(true)}
                      className="text-xs text-slate-400 hover:text-primary transition-colors"
                    >
                      Forgot Password?
                    </button>
                  )}
                </div>
              </form>

              <p className="text-center text-[10px] text-slate-400 font-mono uppercase tracking-widest mt-4">
                Secure Access Only • Authorized Personnel
              </p>
            </div>
          </div>
        </motion.div>

        {}
        {showForgotPassword && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={() => setShowForgotPassword(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="relative z-10 w-full max-w-md mx-4 bg-white rounded-2xl p-6 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setShowForgotPassword(false)}
                className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>

              <div className="text-center mb-6">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-3">
                  <KeyRound className="w-6 h-6 text-primary" />
                </div>
                <h2 className="text-xl font-bold text-slate-900">Reset Password</h2>
                <p className="text-sm text-slate-500 mt-1">
                  {forgotStep === 1 && 'Enter your email to receive OTP'}
                  {forgotStep === 2 && 'Enter the OTP sent to your email'}
                  {forgotStep === 3 && 'Enter your new password'}
                </p>
              </div>

              <form onSubmit={forgotStep === 1 ? handleRequestOTP : forgotStep === 2 ? handleVerifyOTP : handleResetPassword} className="space-y-4">
                {forgotStep === 1 && (
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="email"
                      placeholder="Enter your email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      required
                    />
                  </div>
                )}

                {forgotStep === 2 && (
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Enter OTP"
                      value={forgotOTP}
                      onChange={(e) => setForgotOTP(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      required
                    />
                  </div>
                )}

                {forgotStep === 3 && (
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="password"
                      placeholder="New password"
                      value={forgotNewPassword}
                      onChange={(e) => setForgotNewPassword(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-lg text-slate-900 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      required
                    />
                  </div>
                )}

                <div className="flex gap-3">
                  {forgotStep > 1 && (
                    <Button
                      type="button"
                      onClick={() => setForgotStep(forgotStep - 1)}
                      variant="outline"
                      className="flex-1"
                    >
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      Back
                    </Button>
                  )}
                  <Button
                    type="submit"
                    disabled={forgotLoading}
                    className="flex-1"
                  >
                    {forgotLoading ? 'Processing...' : (
                      forgotStep === 1 ? 'Send OTP' :
                      forgotStep === 2 ? 'Verify OTP' : 'Reset Password'
                    )}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}