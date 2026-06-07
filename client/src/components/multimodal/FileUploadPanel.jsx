import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Upload, FileText, Image, X, AlertCircle, CheckCircle, Loader, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { uploadMultimodalFile } from '../../services/copilotService';
import { toast } from 'sonner';

function buildTicketText(result) {
  const content = result.cleaned_extracted_text || result.extracted_text;
  if (!content || content.startsWith('[')) return '';
  return `[Extracted Content]\n${content.slice(0, 1000)}`;
}

export function FileUploadPanel({ onAnalyzed }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ACCEPT = '.png,.jpg,.jpeg,.webp,.log,.txt';

  const process = useCallback(async (f) => {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const data = await uploadMultimodalFile(f);
      setResult(data);
      onAnalyzed?.(data);
      toast.success(
        data.analysis
          ? 'Image analyzed — ticket fields updated'
          : 'File processed — ticket fields updated',
      );
    } catch (e) {
      setError(e.message || 'Processing failed');
      toast.error(e.message || 'File processing failed');
    } finally {
      setLoading(false);
    }
  }, [onAnalyzed]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) process(f);
  }, [process]);

  const onInputChange = (e) => {
    const f = e.target.files?.[0];
    if (f) process(f);
  };

  const handleReapply = () => {
    if (!result) return;
    onAnalyzed?.(result);
    toast.success('Analysis re-applied to ticket');
  };

  const confidenceColor = (v) => v >= 80 ? '#10b981' : v >= 60 ? '#f59e0b' : '#ef4444';
  const isImage = file?.name?.match(/\.(png|jpg|jpeg|webp)$/i);

  return (
    <div className="space-y-3">
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`relative border-2 border-dashed rounded-xl p-4 text-center transition-all cursor-pointer ${dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-slate-300 bg-slate-50/60'}`}
        onClick={() => document.getElementById('nexus-file-input').click()}
      >
        <input id="nexus-file-input" type="file" accept={ACCEPT} className="hidden" onChange={onInputChange} />
        <div className="flex flex-col items-center gap-1.5">
          <Upload className="w-5 h-5 text-slate-400" />
          <p className="text-[10px] font-semibold text-slate-600">Drop screenshot or log file</p>
          <p className="text-[9px] font-mono text-slate-400">PNG · JPG · LOG · TXT · Max 5 MB</p>
        </div>
      </div>

      <AnimatePresence>
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-indigo-100 bg-indigo-50"
          >
            <Loader className="w-3.5 h-3.5 text-indigo-500 animate-spin" />
            <p className="text-[10px] text-indigo-700 font-medium">
              {isImage ? 'Running OCR and AI analysis...' : 'Parsing log and running AI analysis...'}
            </p>
          </motion.div>
        )}

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-red-200 bg-red-50"
          >
            <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
            <p className="text-[10px] text-red-700">{error}</p>
          </motion.div>
        )}

        {result && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-2">
            <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  {result.file_type === 'image' ? <Image className="w-3.5 h-3.5 text-indigo-500" /> : <FileText className="w-3.5 h-3.5 text-slate-500" />}
                  <p className="text-[10px] font-bold text-slate-700 truncate max-w-[140px]">{file?.name}</p>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[8px] font-mono px-1.5 py-0.5 rounded border"
                    style={{ color: confidenceColor(result.confidence), borderColor: confidenceColor(result.confidence), background: `${confidenceColor(result.confidence)}15` }}>
                    {result.confidence}% confident
                  </span>
                  <button onClick={() => { setFile(null); setResult(null); }} className="w-4 h-4 flex items-center justify-center text-slate-400 hover:text-slate-600">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {result.analysis && (
                <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-2.5 py-1.5 space-y-1">
                  <p className="text-[9px] font-mono text-indigo-600 uppercase tracking-wider flex items-center gap-1">
                    <Brain className="w-3 h-3" /> AI Triage
                  </p>
                  <p className="text-[10px] text-indigo-900 font-medium">{result.analysis.intent}</p>
                  <div className="flex flex-wrap gap-1">
                    <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-white text-indigo-700 border border-indigo-200">
                      {result.analysis.suggestedCategory}
                    </span>
                    <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-white text-indigo-700 border border-indigo-200">
                      {result.analysis.suggestedPriority} priority
                    </span>
                    {result.analysis.confidenceScore != null && (
                      <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-white text-indigo-700 border border-indigo-200">
                        {Math.round(result.analysis.confidenceScore * 100)}% match
                      </span>
                    )}
                  </div>
                  {result.analysis.summary && (
                    <p className="text-[9px] text-indigo-800">{result.analysis.summary}</p>
                  )}
                </div>
              )}

              {result.suggested_title && (
                <div className="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5">
                  <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider mb-0.5">Suggested Title</p>
                  <p className="text-[10px] text-slate-700">{result.suggested_title}</p>
                </div>
              )}

              {result.probable_cause && (
                <div className="rounded-lg border border-amber-100 bg-amber-50 px-2.5 py-1.5">
                  <p className="text-[9px] font-mono text-amber-600 uppercase tracking-wider mb-0.5">Probable Cause</p>
                  <p className="text-[10px] text-amber-800">{result.probable_cause}</p>
                </div>
              )}

              {result.detected_errors?.length > 0 && (
                <div>
                  <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider mb-1">Detected Errors</p>
                  <div className="flex flex-wrap gap-1">
                    {result.detected_errors.slice(0, 8).map((e, i) => (
                      <span key={i} className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">{e}</span>
                    ))}
                  </div>
                </div>
              )}

              {(result.cleaned_extracted_text || result.extracted_text) && (
                <div>
                  <p className="text-[9px] font-mono text-slate-400 uppercase tracking-wider mb-1">Goes into Ticket</p>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 px-2.5 py-2 max-h-24 overflow-y-auto">
                    <p className="text-[9px] font-mono text-slate-600 whitespace-pre-wrap">{buildTicketText(result)}</p>
                  </div>
                </div>
              )}
            </div>

            <Button size="sm" onClick={handleReapply} className="w-full h-8 text-[10px] font-mono uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white">
              <CheckCircle className="w-3 h-3 mr-1.5" /> Re-apply to Ticket
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export { buildTicketText };
