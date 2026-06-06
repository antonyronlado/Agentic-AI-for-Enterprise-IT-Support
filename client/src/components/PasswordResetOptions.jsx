import { Input } from '@/components/ui/input';
import { KeyRound, Sparkles, ShieldCheck } from 'lucide-react';

export function PasswordResetOptions({
  consent,
  onConsentChange,
  mode,
  onModeChange,
  preferredPassword,
  onPreferredPasswordChange,
  compact = false,
}) {
  return (
    <div
      className={`rounded-xl border-2 border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50/50 space-y-3 ${
        compact ? 'p-3' : 'p-4'
      }`}
    >
      <div className="flex items-start gap-2">
        <KeyRound className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
        <div>
          <p className="text-xs font-semibold text-amber-900">
            Password reset detected
          </p>
          <p className="text-[10px] text-amber-800/90 mt-0.5 leading-relaxed">
            Should AI reset your account password? Choose auto-generate or set your own new password.
          </p>
        </div>
      </div>

      <label className="flex items-start gap-2 cursor-pointer rounded-lg border border-amber-200/80 bg-white/70 p-2.5">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => onConsentChange(e.target.checked)}
          className="mt-0.5 accent-amber-600"
        />
        <span className="text-[11px] text-slate-700 leading-snug">
          <ShieldCheck className="w-3 h-3 inline mr-1 text-emerald-600" />
          Yes, allow AI to reset my password for this account
        </span>
      </label>

      {consent && (
        <div className="space-y-2 pl-1">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="passwordResetMode"
              checked={mode === 'auto'}
              onChange={() => onModeChange('auto')}
              className="accent-indigo-600"
            />
            <Sparkles className="w-3 h-3 text-indigo-500" />
            <span className="text-[11px] text-slate-700">Generate a secure password for me</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="passwordResetMode"
              checked={mode === 'custom'}
              onChange={() => onModeChange('custom')}
              className="accent-indigo-600"
            />
            <KeyRound className="w-3 h-3 text-indigo-500" />
            <span className="text-[11px] text-slate-700">Set my own new password</span>
          </label>
          {mode === 'custom' && (
            <Input
              type="password"
              placeholder="Enter new password (min 6 characters)"
              value={preferredPassword}
              onChange={(e) => onPreferredPasswordChange(e.target.value)}
              className="h-9 text-sm bg-white"
            />
          )}
        </div>
      )}
    </div>
  );
}