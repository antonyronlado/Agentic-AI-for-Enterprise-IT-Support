import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { GitMerge, RefreshCw, Users, ChevronRight, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getIncidents, triggerClustering, resolveIncident } from '../../services/aiEngine';
import { toast } from 'sonner';

const SEVERITY_STYLE = {
  high:   'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low:    'bg-emerald-50 text-emerald-700 border-emerald-200',
};

function ConfidenceBar({ value }) {
  const color = value >= 80 ? '#10b981' : value >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
        <motion.div className="h-1 rounded-full" style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.7 }} />
      </div>
      <span className="text-[9px] font-mono" style={{ color }}>{value}%</span>
    </div>
  );
}

export function IncidentClusterView() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clustering, setClustering] = useState(false);
  const [selected, setSelected] = useState(null);

  const fetchIncidents = async () => {
    try {
      const data = await getIncidents();
      setIncidents(data);
    } catch {
      toast.error('Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchIncidents(); }, []);

  const handleCluster = async () => {
    setClustering(true);
    try {
      const result = await triggerClustering();
      toast.success(`RCA complete — ${result.clusters_found} incident cluster(s) identified`);
      await fetchIncidents();
    } catch {
      toast.error('Clustering failed');
    } finally {
      setClustering(false);
    }
  };

  const handleResolve = async (id) => {
    try {
      await resolveIncident(id);
      toast.success('Incident resolved');
      setSelected(null);
      await fetchIncidents();
    } catch {
      toast.error('Failed to resolve incident');
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-slate-900 tracking-tight">Root Cause Analysis</h2>
          <p className="text-sm text-slate-500 mt-0.5">DBSCAN-based incident clustering — semantic similarity grouping</p>
        </div>
        <Button
          onClick={handleCluster}
          disabled={clustering}
          className="bg-indigo-600 hover:bg-indigo-700 text-white h-9 px-4 text-xs font-bold"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-2 ${clustering ? 'animate-spin' : ''}`} />
          {clustering ? 'Analyzing...' : 'Re-Analyze'}
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-32 rounded-2xl bg-slate-100 animate-pulse" />)}
        </div>
      ) : incidents.length === 0 ? (
        <div className="text-center py-20">
          <GitMerge className="w-10 h-10 text-slate-200 mx-auto mb-4" />
          <p className="text-sm font-bold text-slate-400">No incident clusters detected</p>
          <p className="text-[10px] font-mono text-slate-300 uppercase tracking-wider mt-1">
            At least 2 semantically similar tickets are required to form a cluster
          </p>
          <Button onClick={handleCluster} disabled={clustering} variant="outline" className="mt-4 text-xs">
            Run Analysis
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          <AnimatePresence>
            {incidents.map((inc, i) => (
              <motion.div
                key={inc._id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`rounded-2xl border bg-white p-5 shadow-sm cursor-pointer transition-all hover:shadow-md ${selected?._id === inc._id ? 'ring-2 ring-indigo-500/30 border-indigo-200' : 'border-slate-200'}`}
                onClick={() => setSelected(selected?._id === inc._id ? null : inc)}
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded-md border ${SEVERITY_STYLE[inc.severity] || SEVERITY_STYLE.low}`}>
                        {inc.severity} severity
                      </span>
                      <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md border border-indigo-100 bg-indigo-50 text-indigo-600">
                        {inc.category}
                      </span>
                      {inc.status === 'resolved' && (
                        <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-md border border-emerald-100 bg-emerald-50 text-emerald-600">
                          resolved
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 truncate">{inc.title}</h3>
                  </div>
                  <div className="flex items-center gap-4 shrink-0 text-center">
                    <div>
                      <p className="text-lg font-black text-slate-900 leading-none">{inc.affected_ticket_ids?.length || 0}</p>
                      <p className="text-[8px] font-mono text-slate-400 uppercase">tickets</p>
                    </div>
                    <div>
                      <p className="text-lg font-black text-indigo-600 leading-none">{inc.affected_user_count || 0}</p>
                      <p className="text-[8px] font-mono text-slate-400 uppercase">users</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  <p className="text-[10px] text-slate-600">{inc.probable_root_cause}</p>
                </div>

                {inc.cluster_confidence != null && (
                  <div className="mb-3">
                    <div className="flex justify-between mb-1">
                      <span className="text-[9px] font-mono text-slate-400">Cluster Confidence</span>
                    </div>
                    <ConfidenceBar value={inc.cluster_confidence} />
                  </div>
                )}

                <AnimatePresence>
                  {selected?._id === inc._id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="pt-3 border-t border-slate-100 space-y-3">
                        <div className="space-y-1">
                          <p className="text-[9px] font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1">
                            <GitMerge className="w-3 h-3" /> Linked Tickets
                          </p>
                          {(inc.affected_ticket_ids || []).map(tid => (
                            <div key={tid} className="flex items-center gap-2 py-1">
                              <div className="w-1 h-1 rounded-full bg-indigo-300 ml-1 shrink-0" />
                              <span className="text-[9px] font-mono text-slate-500">#{tid.slice(0, 12)}...</span>
                            </div>
                          ))}
                        </div>
                        {inc.status !== 'resolved' && (
                          <Button
                            size="sm"
                            onClick={e => { e.stopPropagation(); handleResolve(inc._id); }}
                            className="w-full h-8 text-[10px] bg-emerald-500 hover:bg-emerald-600 text-white"
                          >
                            <CheckCircle className="w-3 h-3 mr-1.5" /> Mark Cluster Resolved
                          </Button>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}