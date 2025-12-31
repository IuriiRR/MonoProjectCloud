import React, { useEffect, useMemo, useState } from 'react';
import { User } from 'firebase/auth';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCcw, FileText } from 'lucide-react';
import { fetchDailyReport, DailyReportResponse } from '../services/api';

interface ReportProps {
  user: User;
}

function todayIsoDate(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

const Report: React.FC<ReportProps> = ({ user }) => {
  const navigate = useNavigate();
  const defaultTz = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Kyiv', []);

  const [date, setDate] = useState<string>(todayIsoDate());
  const [tz, setTz] = useState<string>(defaultTz);
  // Default OFF to avoid burning strict RPM limits. User can enable when needed.
  const [useLlm, setUseLlm] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [report, setReport] = useState<DailyReportResponse | null>(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchDailyReport(user.uid, { date, tz, llm: useLlm });
      setReport(res);
    } catch (e: any) {
      setError(e?.message || 'Failed to load report');
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.uid]);

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-8 pt-12">
      <button
        onClick={() => navigate('/')}
        className="flex items-center text-zinc-400 hover:text-white mb-10 transition-colors group"
      >
        <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>

      <div className="glass-card p-8">
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center">
            <div className="p-3 bg-white/5 rounded-xl border border-white/10 mr-4">
              <FileText className="text-white" size={22} />
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight">Daily Report</h2>
              <p className="text-sm text-zinc-500">Covered vs uncovered spends across cards + jars</p>
            </div>
          </div>
          <button
            onClick={load}
            className="flex items-center px-4 py-2 text-sm font-medium bg-zinc-900 border border-white/10 rounded-lg hover:border-white/30 transition-all"
            disabled={loading}
            title="Refresh"
          >
            <RefreshCcw size={18} className={loading ? 'animate-spin mr-2' : 'mr-2'} />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div>
            <label className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="block w-full pl-4 pr-4 py-3 bg-zinc-950 border border-white/10 text-white rounded-lg focus:outline-none focus:border-white/30 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Timezone</label>
            <input
              value={tz}
              onChange={(e) => setTz(e.target.value)}
              placeholder="Europe/Kyiv"
              className="block w-full pl-4 pr-4 py-3 bg-zinc-950 border border-white/10 text-white rounded-lg focus:outline-none focus:border-white/30 transition-all"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                className="h-4 w-4 accent-white"
              />
              <span className="text-sm text-zinc-300">Use Gemini agent loop (if configured)</span>
            </label>
          </div>
        </div>

        <div className="flex gap-3 mb-8">
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center justify-center px-5 py-3 btn-primary shadow-glow-white disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Generate report'}
          </button>
        </div>

        {error ? (
          <div className="p-4 mb-6 text-red-400 bg-red-950/20 border border-red-900/50 rounded-xl">
            {error}
          </div>
        ) : null}

        {report ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <div className="p-4 rounded-xl border border-white/10 bg-white/5">
                <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">Spends</p>
                <p className="text-2xl font-black mt-1">{(report.totals.spend_total / 100).toFixed(2)}</p>
              </div>
              <div className="p-4 rounded-xl border border-white/10 bg-white/5">
                <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">Earnings</p>
                <p className="text-2xl font-black mt-1">{(report.totals.earn_total / 100).toFixed(2)}</p>
              </div>
              <div className="p-4 rounded-xl border border-white/10 bg-white/5">
                <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">Net</p>
                <p className="text-2xl font-black mt-1">{(report.totals.net / 100).toFixed(2)}</p>
              </div>
            </div>

            {report.report_html ? (
              <div
                className="prose prose-invert max-w-none p-6 rounded-xl border border-white/10 bg-zinc-950"
                dangerouslySetInnerHTML={{ __html: report.report_html }}
              />
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed p-6 rounded-xl border border-white/10 bg-zinc-950 text-zinc-200">
                {report.report_markdown}
              </pre>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
};

export default Report;

