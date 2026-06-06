import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { TrendingUp, TrendingDown, Minus, BarChart3, AlertTriangle, RefreshCw, Zap, Clock, Shield, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getAnalyticsOverview, getAnalyticsTrends, getTrendIntelligence } from '../../services/analyticsService';

function KPICard({ label, value, unit = '', icon: Icon, color, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="rounded-2xl border border-white/10 p-5 flex flex-col gap-3"
      style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(16px)' }}
    >
      <div className="flex items-center justify-between">
        <p className="text-[9px] font-mono uppercase tracking-widest text-white/50">{label}</p>
        {Icon && <Icon className={`w-4 h-4 ${color}`} />}
      </div>
      <p className={`text-3xl font-black tabular-nums leading-none ${color}`}>
        {value}<span className="text-sm font-normal text-white/40 ml-1">{unit}</span>
      </p>
    </motion.div>
  );
}

function TrendChart({ data }) {
  if (!data?.length) return null;
  const max = Math.max(...data.map(d => d.count), 1);
  const W = 300, H = 80;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - (d.count / max) * (H - 10);
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 80 }}>
      <defs>
        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${H} ${pts} ${W},${H}`}
        fill="url(#chartFill)"
      />
      <polyline
        points={pts}
        fill="none"
        stroke="#6366f1"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {data.map((d, i) => {
        const x = (i / (data.length - 1)) * W;
        const y = H - (d.count / max) * (H - 10);
        return (
          <g key={i}>
            <circle cx={x} cy={y} r="3" fill="#6366f1" />
            <text x={x} y={H - 2} textAnchor="middle" fontSize="7" fill="rgba(255,255,255,0.4)" fontFamily="monospace">
              {d.date}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function DonutChart({ data }) {
  if (!data?.length) return null;
  const total = data.reduce((s, d) => s + d.count, 0) || 1;
  const COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'];
  let cumulative = 0;

  const arcs = data.map((d, i) => {
    const pct = d.count / total;
    const startAngle = cumulative * 2 * Math.PI;
    cumulative += pct;
    const endAngle = cumulative * 2 * Math.PI;
    const R = 36, r = 22, cx = 40, cy = 40;
    const x1 = cx + R * Math.sin(startAngle), y1 = cy - R * Math.cos(startAngle);
    const x2 = cx + R * Math.sin(endAngle), y2 = cy - R * Math.cos(endAngle);
    const ix1 = cx + r * Math.sin(startAngle), iy1 = cy - r * Math.cos(startAngle);
    const ix2 = cx + r * Math.sin(endAngle), iy2 = cy - r * Math.cos(endAngle);
    const large = pct > 0.5 ? 1 : 0;
    return { d: `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${r} ${r} 0 ${large} 0 ${ix1} ${iy1} Z`, color: COLORS[i % COLORS.length], ...d };
  });

  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 80 80" className="w-20 h-20 shrink-0">
        {arcs.map((a, i) => <path key={i} d={a.d} fill={a.color} opacity="0.85" />)}
      </svg>
      <div className="space-y-1.5 flex-1">
        {data.map((d, i) => (
          <div key={i} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
              <span className="text-[9px] font-mono text-white/60 capitalize">{d.category}</span>
            </div>
            <span className="text-[9px] font-mono text-white/80 tabular-nums">{d.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Heatmap({ data }) {
  if (!data?.length) return null;
  const cats = ['software', 'hardware', 'access', 'network', 'other'];
  const maxVal = Math.max(...data.flatMap(row => cats.map(c => row[c] || 0)), 1);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[9px] font-mono">
        <thead>
          <tr>
            <th className="text-left text-white/40 pb-1.5 font-normal w-8">Day</th>
            {cats.map(c => <th key={c} className="text-center text-white/40 pb-1.5 font-normal capitalize px-1">{c.slice(0, 3)}</th>)}
          </tr>
        </thead>
        <tbody className="space-y-1">
          {data.map((row, i) => (
            <tr key={i}>
              <td className="text-white/50 pr-2">{row.day}</td>
              {cats.map(c => {
                const v = row[c] || 0;
                const intensity = v / maxVal;
                return (
                  <td key={c} className="px-1 py-0.5 text-center">
                    <div className="w-full h-6 rounded flex items-center justify-center text-[8px] font-bold transition-all"
                      style={{ background: `hsla(238, 84%, 67%, ${intensity * 0.8 + 0.05})`, color: intensity > 0.4 ? 'white' : 'rgba(255,255,255,0.3)' }}>
                      {v > 0 ? v : ''}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AnalyticsDashboard() {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const [ov, tr, ti] = await Promise.all([
        getAnalyticsOverview(),
        getAnalyticsTrends(),
        getTrendIntelligence(),
      ]);
      setOverview(ov);
      setTrends(tr);
      setIntelligence(ti);
    } catch (e) {
      console.error('Analytics load failed', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const weekTrend = intelligence?.week_comparison;
  const TrendIcon = weekTrend?.trend === 'up' ? TrendingUp : weekTrend?.trend === 'down' ? TrendingDown : Minus;
  const trendColor = weekTrend?.trend === 'up' ? 'text-red-400' : weekTrend?.trend === 'down' ? 'text-emerald-400' : 'text-slate-400';

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto w-full space-y-6"
      style={{ background: 'linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0f1729 100%)', minHeight: '100%' }}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" /> Enterprise Analytics
          </h2>
          <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest mt-0.5">
            Incident Trend Intelligence · Real-time Metrics
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => load(true)}
          disabled={refreshing}
          className="h-8 text-[10px] border-white/20 text-white/70 hover:text-white hover:bg-white/10 bg-transparent"
        >
          <RefreshCw className={`w-3 h-3 mr-1.5 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-28 rounded-2xl bg-white/5 animate-pulse" />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard label="AI Resolution Rate" value={overview?.ai_resolution_pct ?? 0} unit="%" icon={Zap} color="text-indigo-400" delay={0} />
            <KPICard label="SLA Compliance" value={overview?.sla_compliance ?? 0} unit="%" icon={Shield} color="text-emerald-400" delay={0.05} />
            <KPICard label="Escalation Rate" value={overview?.escalation_rate ?? 0} unit="%" icon={AlertTriangle} color="text-amber-400" delay={0.1} />
            <KPICard label="Avg Resolution" value={overview?.avg_resolution_minutes ?? 0} unit="min" icon={Clock} color="text-cyan-400" delay={0.15} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="rounded-2xl border border-white/10 p-5 space-y-3"
              style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(16px)' }}>
              <div className="flex items-center justify-between">
                <p className="text-[9px] font-mono uppercase tracking-widest text-white/50">7-Day Ticket Volume</p>
                {weekTrend && (
                  <div className={`flex items-center gap-1 ${trendColor}`}>
                    <TrendIcon className="w-3 h-3" />
                    <span className="text-[9px] font-mono">{weekTrend.pct_change > 0 ? '+' : ''}{weekTrend.pct_change}% vs last week</span>
                  </div>
                )}
              </div>
              <TrendChart data={trends?.daily_volume} />
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
              className="rounded-2xl border border-white/10 p-5 space-y-3"
              style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(16px)' }}>
              <p className="text-[9px] font-mono uppercase tracking-widest text-white/50">Category Distribution</p>
              <DonutChart data={trends?.category_trends} />
            </motion.div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="rounded-2xl border border-white/10 p-5 space-y-3"
              style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(16px)' }}>
              <p className="text-[9px] font-mono uppercase tracking-widest text-white/50">Incident Heatmap — Tickets by Category & Day</p>
              <Heatmap data={intelligence?.heatmap} />
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
              className="rounded-2xl border border-white/10 p-5 space-y-3"
              style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(16px)' }}>
              <p className="text-[9px] font-mono uppercase tracking-widest text-white/50">Status Breakdown</p>
              {overview?.by_status && Object.entries(overview.by_status).map(([k, v]) => {
                const total = overview.total || 1;
                const pct = Math.round((v / total) * 100);
                const colors = { resolved: '#10b981', open: '#6366f1', in_progress: '#f59e0b', escalated: '#ef4444', failed: '#dc2626', linked: '#8b5cf6' };
                return (
                  <div key={k} className="space-y-0.5">
                    <div className="flex justify-between">
                      <span className="text-[9px] font-mono text-white/50 capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="text-[9px] font-mono text-white/70">{v}</span>
                    </div>
                    <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                      <motion.div className="h-1 rounded-full" style={{ background: colors[k] || '#6366f1' }}
                        initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, delay: 0.4 }} />
                    </div>
                  </div>
                );
              })}
            </motion.div>
          </div>

          {(trends?.spike_alerts?.length > 0 || intelligence?.anomalies?.length > 0) && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
              className="rounded-2xl border border-amber-500/20 p-5 space-y-2"
              style={{ background: 'rgba(245,158,11,0.07)', backdropFilter: 'blur(16px)' }}>
              <p className="text-[9px] font-mono uppercase tracking-widest text-amber-400/80 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Spike Alerts & Anomalies
              </p>
              {[...(trends?.spike_alerts || []), ...(intelligence?.anomalies || [])].map((a, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${a.severity === 'high' ? 'bg-red-400 animate-pulse' : 'bg-amber-400'}`} />
                  <p className="text-[10px] text-white/70">{a.message}</p>
                </div>
              ))}
            </motion.div>
          )}

          {intelligence?.recurring_issues?.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}
              className="rounded-2xl border border-white/10 p-5 space-y-3"
              style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(16px)' }}>
              <p className="text-[9px] font-mono uppercase tracking-widest text-white/50">Recurring Issues (Last 7 Days)</p>
              <div className="space-y-2">
                {intelligence.recurring_issues.map((issue, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-[10px] font-black text-white/30 w-4 shrink-0">{i + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-[10px] text-white/70 capitalize">{issue.label}</span>
                        <span className="text-[9px] font-mono text-white/50">{issue.count}×</span>
                      </div>
                      <div className="h-0.5 bg-white/10 rounded-full">
                        <div className="h-0.5 bg-indigo-400 rounded-full" style={{ width: `${Math.min((issue.count / 10) * 100, 100)}%` }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </>
      )}
    </div>
  );
}