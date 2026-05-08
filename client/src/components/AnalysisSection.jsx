import { motion } from 'motion/react';
import {
  Brain, Shield, CheckCircle2, Lightbulb, AlertTriangle,
  ShieldAlert, Lock, Zap, ChevronRight,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────
//  Confidence bar shown inside NLP section
// ─────────────────────────────────────────────────────────
function ConfidenceBar({ score, label }) {
  if (score == null) return null;
  const pct   = Math.min(100, Math.max(0, score));
  const color = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  const text  = pct >= 75 ? 'text-emerald-700' : pct >= 50 ? 'text-amber-700' : 'text-red-700';
  const reliability = pct >= 75 ? 'High Reliability' : pct >= 50 ? 'Medium Reliability' : 'Low — Review Needed';

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{label || 'AI Confidence'}</p>
        <span className={`text-xs font-bold font-mono ${text}`}>
          {pct}% · {reliability}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-200/80 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1], delay: 0.1 }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
//  Individual analysis section block
// ─────────────────────────────────────────────────────────
const SECTION_META = {
  'NLP ANALYSIS': {
    icon: Brain,
    accent: 'border-indigo-200/80 bg-gradient-to-br from-indigo-50/60 to-violet-50/30',
    headerColor: 'text-indigo-600',
    iconBg: 'bg-indigo-100',
  },
  'RISK ASSESSMENT': {
    icon: Shield,
    accent: 'border-amber-200/80 bg-gradient-to-br from-amber-50/60 to-orange-50/30',
    headerColor: 'text-amber-700',
    iconBg: 'bg-amber-100',
    // dynamic — overridden by risk level
  },
  'RESOLUTION PATH': {
    icon: CheckCircle2,
    accent: 'border-emerald-200/80 bg-gradient-to-br from-emerald-50/60 to-teal-50/30',
    headerColor: 'text-emerald-700',
    iconBg: 'bg-emerald-100',
  },
  'RECOMMENDED ACTIONS': {
    icon: Lightbulb,
    accent: 'border-blue-200/80 bg-gradient-to-br from-blue-50/60 to-sky-50/30',
    headerColor: 'text-blue-700',
    iconBg: 'bg-blue-100',
  },
};

function AnalysisSectionBlock({ header, body, index, riskLevel }) {
  const meta = SECTION_META[header] || SECTION_META['NLP ANALYSIS'];
  const Icon = meta.icon;

  // Dynamically adjust Risk Assessment colors based on riskLevel
  let accent       = meta.accent;
  let headerColor  = meta.headerColor;
  let iconBg       = meta.iconBg;
  if (header === 'RISK ASSESSMENT' && riskLevel) {
    if (riskLevel === 'high') {
      accent      = 'border-red-200/80 bg-gradient-to-br from-red-50/60 to-rose-50/30';
      headerColor = 'text-red-700';
      iconBg      = 'bg-red-100';
    } else if (riskLevel === 'medium') {
      accent      = 'border-amber-200/80 bg-gradient-to-br from-amber-50/60 to-orange-50/30';
      headerColor = 'text-amber-700';
      iconBg      = 'bg-amber-100';
    } else {
      accent      = 'border-emerald-200/80 bg-gradient-to-br from-emerald-50/60 to-teal-50/30';
      headerColor = 'text-emerald-700';
      iconBg      = 'bg-emerald-100';
    }
  }

  // Format body lines as a structured list if they contain numbered items
  const lines = body.split('\n').filter(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08, ease: [0.4, 0, 0.2, 1] }}
      className={`rounded-xl border p-4 space-y-3 ${accent}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${iconBg}`}>
          <Icon className={`w-3.5 h-3.5 ${headerColor}`} />
        </div>
        <p className={`text-[10px] font-mono font-bold uppercase tracking-widest ${headerColor}`}>
          {header}
        </p>
      </div>

      {/* Body */}
      <div className="space-y-1.5">
        {lines.map((line, i) => {
          // Numbered step or bullet
          const numbered = /^\d+\.\s/.test(line);
          const keyval   = /^[\w\s]+:\s/.test(line) && !numbered;

          if (numbered) {
            const [, num, rest] = line.match(/^(\d+)\.\s(.+)/) || [, '', line];
            return (
              <div key={i} className="flex items-start gap-2">
                <span className={`
                  mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0
                  text-[9px] font-mono font-bold bg-white/70 border border-current/20
                  ${headerColor}
                `}>
                  {num}
                </span>
                <p className="text-xs text-slate-700 leading-relaxed">{rest}</p>
              </div>
            );
          }

          if (keyval) {
            const colonIdx = line.indexOf(':');
            const key      = line.slice(0, colonIdx).trim();
            const val      = line.slice(colonIdx + 1).trim();
            return (
              <div key={i} className="flex items-start gap-2">
                <span className={`text-[9px] font-mono uppercase tracking-wide shrink-0 pt-0.5 ${headerColor} opacity-70`}>
                  {key}
                </span>
                <ChevronRight className="w-3 h-3 mt-0.5 shrink-0 text-slate-400" />
                <p className="text-xs text-slate-700 leading-relaxed">{val}</p>
              </div>
            );
          }

          return (
            <p key={i} className="text-xs text-slate-700 leading-relaxed">{line}</p>
          );
        })}
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────
//  Risk summary card (standalone, used above tabs)
// ─────────────────────────────────────────────────────────
export function RiskSummaryCard({ risk, confidenceScore, updatedAt }) {
  if (!risk) return null;
  const level = risk.risk_level || risk.impact || 'low';

  const colors = {
    low:    { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', dot: 'bg-emerald-500' },
    medium: { bg: 'bg-amber-50',   border: 'border-amber-200',   text: 'text-amber-700',   dot: 'bg-amber-500' },
    high:   { bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-700',      dot: 'bg-red-500' },
  };
  const c = colors[level] || colors.low;

  function getAgeLabel(ts) {
    const diffMin = Math.floor((Date.now() - ts) / 60000);
    if (diffMin < 60)   return `${diffMin}m ago`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
    return `${Math.floor(diffMin / 1440)}d ago`;
  }

  const isSlaWarning = (() => {
    const diffMin = Math.floor((Date.now() - updatedAt) / 60000);
    return diffMin > 60;
  })();

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border p-4 space-y-3 ${c.bg} ${c.border}`}
    >
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="relative">
            <span className={`w-2.5 h-2.5 rounded-full block ${c.dot}`} />
          </div>
          <p className={`text-[10px] font-mono uppercase tracking-widest font-bold ${c.text}`}>
            Risk Level: {level.toUpperCase()}
          </p>
          {risk.securityRisk && (
            <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-full border bg-red-100 text-red-700 border-red-300">
              <ShieldAlert className="w-2.5 h-2.5" /> Security Risk
            </span>
          )}
          {risk.escalate && (
            <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-full border bg-orange-100 text-orange-700 border-orange-300">
              <AlertTriangle className="w-2.5 h-2.5" /> Escalated
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isSlaWarning && (
            <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-2 py-0.5 rounded-full border bg-orange-50 text-orange-700 border-orange-300 animate-pulse">
              SLA Warning
            </span>
          )}
          <span className="text-[9px] font-mono text-slate-400">{getAgeLabel(updatedAt)}</span>
        </div>
      </div>

      {confidenceScore != null && (
        <ConfidenceBar score={confidenceScore} label="AI Confidence Score" />
      )}

      {risk.riskScore !== undefined && (
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-slate-500">Raw Risk Score</span>
          <span className={`font-bold ${c.text}`}>{Math.round(risk.riskScore * 100)}%</span>
        </div>
      )}
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────
//  Full risk assessment tab
// ─────────────────────────────────────────────────────────
export function RiskAssessmentPanel({ risk, confidenceScore }) {
  if (!risk) return (
    <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
      <Shield className="w-10 h-10 text-slate-200 mx-auto mb-3" />
      <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">No risk assessment yet</p>
    </div>
  );

  const level = risk.risk_level || risk.impact || 'low';
  const colors = {
    low:    { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', gridBg: 'bg-emerald-500' },
    medium: { bg: 'bg-amber-50',   border: 'border-amber-200',   text: 'text-amber-700',   gridBg: 'bg-amber-500' },
    high:   { bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-700',      gridBg: 'bg-red-500' },
  };
  const c = colors[level] || colors.low;

  const metrics = [
    {
      label: 'Risk Level',
      value: level.toUpperCase(),
      valueClass: c.text,
    },
    {
      label: 'Confidence',
      value: confidenceScore != null ? `${confidenceScore}%` : 'N/A',
      valueClass: 'text-slate-700',
    },
    {
      label: 'Security Risk',
      value: risk.securityRisk ? '⚠ Detected' : '✓ Clear',
      valueClass: risk.securityRisk ? 'text-red-600' : 'text-emerald-600',
    },
    {
      label: 'Compliance',
      value: risk.complianceCheck ? '✓ Passed' : '✗ Failed',
      valueClass: risk.complianceCheck ? 'text-emerald-600' : 'text-red-600',
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border p-5 space-y-4 ${c.bg} ${c.border}`}
    >
      <div className="flex items-center gap-2">
        <Shield className={`w-4 h-4 ${c.text}`} />
        <p className={`text-xs font-mono uppercase tracking-widest font-bold ${c.text}`}>
          Risk Assessment
        </p>
        {risk.riskScore !== undefined && (
          <span className={`ml-auto text-xs font-mono font-bold ${c.text}`}>
            Score: {Math.round(risk.riskScore * 100)}%
          </span>
        )}
      </div>

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-2">
        {metrics.map(m => (
          <div key={m.label} className="rounded-lg bg-white/80 border border-white p-3 space-y-1">
            <p className="text-[9px] font-mono uppercase text-slate-500 tracking-wider">{m.label}</p>
            <p className={`text-sm font-bold font-mono ${m.valueClass}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {confidenceScore != null && (
        <ConfidenceBar score={confidenceScore} label="AI Confidence" />
      )}

      {risk.notes && (
        <div className="rounded-lg bg-white/80 border border-white p-3 space-y-1">
          <p className="text-[9px] font-mono uppercase text-slate-500 tracking-wider">Agent Notes</p>
          <p className="text-xs text-slate-700 leading-relaxed">{risk.notes}</p>
        </div>
      )}

      {risk.escalate && risk.escalationReason && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 space-y-1">
          <p className="text-[9px] font-mono uppercase text-red-600 tracking-wider">Escalation Reason</p>
          <p className="text-xs text-red-700 leading-relaxed">{risk.escalationReason}</p>
        </div>
      )}
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────
//  Main AnalysisSection — parses and renders admin response
// ─────────────────────────────────────────────────────────
export function AnalysisSection({ text, riskLevel }) {
  if (!text) return (
    <div className="rounded-xl border border-slate-100 bg-white p-12 text-center">
      <Brain className="w-10 h-10 text-slate-200 mx-auto mb-3" />
      <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">No admin analysis yet</p>
    </div>
  );

  // Parse sections by [HEADER] pattern
  const rawSections = text.split('\n\n').filter(Boolean);
  const parsed = rawSections.map(section => {
    const match = section.match(/^\[([^\]]+)\]/);
    if (match) {
      const header = match[1];
      const body   = section.slice(match[0].length).trim();
      return { header, body };
    }
    return { header: null, body: section };
  });

  return (
    <div className="space-y-3">
      {parsed.map((s, i) =>
        s.header ? (
          <AnalysisSectionBlock
            key={i}
            header={s.header}
            body={s.body}
            index={i}
            riskLevel={riskLevel}
          />
        ) : (
          <motion.p
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.06 }}
            className="text-xs text-slate-600 leading-relaxed px-1"
          >
            {s.body}
          </motion.p>
        )
      )}
    </div>
  );
}
