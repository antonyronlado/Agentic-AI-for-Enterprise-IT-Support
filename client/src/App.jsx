import { AuthProvider, useAuth } from './components/AuthGuard';
import { UserDashboard } from './components/UserDashboard';
import { AgentDashboard } from './components/AgentDashboard';
import { Toaster } from '@/components/ui/sonner';

function DashboardRouter() {
  const { profile } = useAuth();

  if (profile?.role === 'agent' || profile?.role === 'admin') {
    return <AgentDashboard />;
  }

  return <UserDashboard />;
}

export default function App() {
  console.log("App component is rendering");
  return (
    <AuthProvider>
      <DashboardRouter />
      <Toaster position="bottom-right" theme="dark" />
    </AuthProvider>
  );
}
