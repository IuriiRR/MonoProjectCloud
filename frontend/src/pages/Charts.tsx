import { User } from 'firebase/auth';
import { ArrowLeft, BarChart3, Info } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import FamilyMemberSelector from '../components/FamilyMemberSelector';
import { Account, FamilyMemberInfo, fetchAccountsCached, fetchBalanceChartData, fetchFamilyMembers, fetchMonthlySummary, MonthlySummary } from '../services/api';

interface ChartsProps {
  user: User;
}

const Charts: React.FC<ChartsProps> = ({ user }) => {
  const [jars, setJars] = useState<Account[]>([]);
  const [chartData, setChartData] = useState<Record<string, any[]>>({});
  const [summaryData, setSummaryData] = useState<Record<string, MonthlySummary[]>>({});
  const [hoveredMonth, setHoveredMonth] = useState<{ jarId: string; summary: MonthlySummary; source: 'chip' | 'chart' } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [budgetOnly, setBudgetOnly] = useState(false);

  // Family state
  const [familyMembers, setFamilyMembers] = useState<FamilyMemberInfo[]>([]);
  const [selectedFamilyUserIds, setSelectedFamilyUserIds] = useState<string[]>([]);

  const navigate = useNavigate();

  useEffect(() => {
    fetchFamilyMembers(user.uid)
      .then((members) => setFamilyMembers(members || []))
      .catch(console.error);
  }, [user.uid]);

  useEffect(() => {
    loadData();
  }, [user.uid, selectedFamilyUserIds.join(','), familyMembers.length]);

  const loadData = async () => {
    try {
      setLoading(true);
      const userIds = [user.uid, ...selectedFamilyUserIds];

      const userPromises = userIds.map(async (uid) => {
        const [accounts, data, summary] = await Promise.all([
          fetchAccountsCached(uid),
          fetchBalanceChartData(uid),
          fetchMonthlySummary(uid)
        ]);
        return {
          uid,
          accounts: accounts.map(a => ({ ...a, ownerId: uid })),
          data,
          summary
        };
      });

      const results = await Promise.all(userPromises);

      // Merge results
      const allAccounts = results.flatMap(r => r.accounts);
      const allData: Record<string, any[]> = {};
      const allSummary: Record<string, MonthlySummary[]> = {};

      results.forEach(r => {
        Object.assign(allData, r.data);
        Object.assign(allSummary, r.summary);
      });

      const filteredJars = allAccounts.filter(acc => acc.type === 'jar');
      setJars(filteredJars);
      setSummaryData(allSummary);

      // Transform data for recharts
      const transformed: Record<string, any[]> = {};
      Object.entries(allData).forEach(([accId, points]) => {
        transformed[accId] = points.map(p => ({
          time: p.time * 1000,
          balance: p.balance / 100,
          rawTime: p.time
        })).sort((a, b) => a.rawTime - b.rawTime);
      });

      setChartData(transformed);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const monthKeyFromUnixSeconds = (unixSeconds: number) => {
    const d = new Date(unixSeconds * 1000);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  };

  const handleChartMouseMove = (jarId: string) => (state: any) => {
    // Only “select” month when hovering a real point (activePayload exists)
    const payload = state?.activePayload?.[0]?.payload;
    if (!payload) return;

    // Prefer the raw seconds timestamp if present; otherwise derive from ms time.
    const rawSeconds =
      typeof payload.rawTime === 'number'
        ? payload.rawTime
        : typeof payload.time === 'number'
          ? Math.floor(payload.time / 1000)
          : null;
    if (!rawSeconds) return;

    const monthKey = monthKeyFromUnixSeconds(rawSeconds);
    const monthSummary = summaryData[jarId]?.find((m) => m.month === monthKey);
    if (!monthSummary) return;

    setHoveredMonth((prev) => {
      // If user is explicitly hovering month chips, don't override.
      if (prev?.source === 'chip' && prev.jarId === jarId) return prev;
      if (prev?.source === 'chart' && prev.jarId === jarId && prev.summary.month === monthKey) return prev;
      return { jarId, summary: monthSummary, source: 'chart' };
    });
  };

  const handleChartMouseLeave = (jarId: string) => () => {
    setHoveredMonth((prev) => {
      if (!prev) return prev;
      if (prev.jarId !== jarId) return prev;
      return prev.source === 'chart' ? null : prev;
    });
  };

  const getAverageStats = (jarId: string) => {
    const data = summaryData[jarId];
    if (!data || data.length === 0) return null;

    // Take last 6 months (data is usually sorted by backend, but let's ensure desc or asc logic)
    const sorted = [...data].sort((a, b) => b.month.localeCompare(a.month)); // Newest first
    const last6 = sorted.slice(0, 6);

    const avgBudget = last6.reduce((sum, item) => sum + item.budget, 0) / last6.length;
    const avgSpent = last6.reduce((sum, item) => sum + item.spent, 0) / last6.length;

    return {
      budget: avgBudget,
      spent: avgSpent,
      count: last6.length
    };
  };

  const getMonthRange = (jarId: string, month: string) => {
    // month string format: "YYYY-MM"
    const [year, monthStr] = month.split('-').map(Number);
    const startDate = new Date(year, monthStr - 1, 1).getTime();
    const endDate = new Date(year, monthStr, 0, 23, 59, 59).getTime(); // Last day of month

    return {
      x1: startDate,
      x2: endDate
    };
  };

  if (loading) return <div className="flex items-center justify-center h-screen">Loading charts...</div>;

  const visibleJars = budgetOnly ? jars.filter(j => Boolean(j.is_budget)) : jars;

  return (
    <div className="min-h-screen bg-black py-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-8">
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-12 gap-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center text-zinc-400 hover:text-white transition-colors group"
          >
            <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Dashboard
          </button>
          <div className="flex flex-col gap-4 items-end">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <h1 className="text-3xl font-bold flex items-center tracking-tight">
                <BarChart3 className="mr-3 text-white" />
                Jar Balance Trends
              </h1>
              <label className="flex items-center gap-3 cursor-pointer select-none self-start sm:self-auto">
                <input
                  type="checkbox"
                  checked={budgetOnly}
                  onChange={(e) => setBudgetOnly(e.target.checked)}
                  className="h-4 w-4 accent-white"
                  aria-label="Show budget jars only"
                />
                <span className="text-sm text-zinc-300">Budget only</span>
              </label>
            </div>
            {familyMembers.length > 0 && (
              <FamilyMemberSelector
                members={familyMembers}
                selectedUserIds={selectedFamilyUserIds}
                onChangeSelectedUserIds={setSelectedFamilyUserIds}
                compact
              />
            )}
          </div>
        </header>

        {error && (
          <div className="p-4 mb-8 text-red-400 bg-red-950/20 border border-red-900/50 rounded-xl">
            {error}
          </div>
        )}

        {visibleJars.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <Info className="mx-auto mb-6 text-zinc-600" size={48} />
            <h2 className="text-2xl font-bold mb-2">No Jars Found</h2>
            <p className="text-zinc-500">
              {budgetOnly
                ? 'No budget jars found. Disable “Budget only” to view all jars.'
                : 'Only accounts of type "jar" are shown on this page.'}
            </p>
          </div>
        ) : (
          <div className="grid gap-12">
            {visibleJars.map(jar => {
              const currentHover = hoveredMonth?.jarId === jar.id ? hoveredMonth.summary : null;
              const averages = !currentHover && summaryData[jar.id] ? getAverageStats(jar.id) : null;
              const isOwner = jar.ownerId === user.uid || !jar.ownerId;

              let activeRange = null;
              if (currentHover) {
                const range = getMonthRange(jar.id, currentHover.month);
                if (range.x1 && range.x2) {
                  activeRange = range;
                }
              }

              return (
                <div key={jar.id} className="glass-card p-8">
                  <div className="mb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-2xl font-bold tracking-tight">{jar.title || 'Untitled Jar'}</h3>
                        {jar.is_budget ? (
                          <span className="text-[11px] font-bold uppercase tracking-widest px-2 py-1 rounded-md border border-white/10 bg-white/5 text-zinc-200">
                            Budget
                          </span>
                        ) : null}
                      </div>
                      <p className="text-sm text-zinc-500 mt-1 font-mono">
                        {jar.id}
                        {!isOwner && <span className="ml-2 text-zinc-500 text-xs border border-zinc-700 px-1 rounded">Read-only</span>}
                      </p>
                    </div>
                    <div className="sm:text-right">
                      <p className="text-xs text-zinc-500 uppercase font-bold tracking-widest">Current Balance</p>
                      <p className="text-2xl font-black mt-1">{(jar.balance / 100).toLocaleString()} <span className="text-sm font-light text-zinc-500">UAH</span></p>
                    </div>
                  </div>

                  {/* Summary Header Area */}
                  <div className="h-16 mb-4 flex items-center">
                    {currentHover ? (
                      <div className="flex gap-8 w-full animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className="flex flex-col">
                          <span className="text-xs text-zinc-500 uppercase font-bold tracking-widest">{currentHover.month} Summary</span>
                        </div>
                        <div className="h-8 w-px bg-white/10 mx-2"></div>
                        <div>
                          <span className="text-xs text-zinc-500 block">Start</span>
                          <span className="font-mono text-sm">{(currentHover.start_balance / 100).toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-xs text-zinc-500 block">End</span>
                          <span className="font-mono text-sm">{(currentHover.end_balance / 100).toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-xs text-zinc-500 block">Budget Income</span>
                          <span className="font-mono text-sm text-emerald-400">+{(currentHover.budget / 100).toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-xs text-zinc-500 block">Spent</span>
                          <span className="font-mono text-sm text-rose-400">{(currentHover.spent / 100).toFixed(2)}</span>
                        </div>
                      </div>
                    ) : averages ? (
                      <div className="flex gap-8 w-full animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className="flex flex-col">
                          <span className="text-xs text-zinc-500 uppercase font-bold tracking-widest">6-Month Average</span>
                          <span className="text-[10px] text-zinc-600">Based on last {averages.count} months</span>
                        </div>
                        <div className="h-8 w-px bg-white/10 mx-2"></div>
                        <div>
                          <span className="text-xs text-zinc-500 block">Avg Budget</span>
                          <span className="font-mono text-sm text-emerald-400/80">+{(averages.budget / 100).toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-xs text-zinc-500 block">Avg Spent</span>
                          <span className="font-mono text-sm text-rose-400/80">{(averages.spent / 100).toFixed(2)}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="h-full flex items-center text-zinc-700 text-sm italic">
                        {jar.is_budget ? 'Hover over a month below to see details.' : ''}
                      </div>
                    )}
                  </div>

                  <div className="h-96 w-full bg-black/40 rounded-xl border border-white/5 p-4 relative">
                    {(!chartData[jar.id] || chartData[jar.id].length === 0) ? (
                      <div className="h-full flex items-center justify-center">
                        <p className="text-zinc-600 text-sm italic">No transaction history found for this jar.</p>
                      </div>
                    ) : (
                      <>
                        <div id={`chart-${jar.id}`} className="w-full h-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                              data={chartData[jar.id]}
                              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                              onMouseMove={handleChartMouseMove(jar.id)}
                              onMouseLeave={handleChartMouseLeave(jar.id)}
                            >
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#18181b" />
                              <XAxis
                                dataKey="time"
                                tick={{ fontSize: 11, fill: '#71717a' }}
                                minTickGap={40}
                                axisLine={false}
                                tickLine={false}
                                tickFormatter={(time) => new Date(time).toLocaleDateString()}
                                type="number"
                                domain={['dataMin', 'dataMax']}
                              />
                              <YAxis
                                tick={{ fontSize: 11, fill: '#71717a' }}
                                tickFormatter={(value) => `${value.toLocaleString()}`}
                                axisLine={false}
                                tickLine={false}
                              />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: '#09090b',
                                  border: '1px solid rgba(255,255,255,0.1)',
                                  borderRadius: '12px',
                                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                                  padding: '12px'
                                }}
                                itemStyle={{ color: '#fff', fontSize: '13px' }}
                                labelStyle={{ color: '#71717a', fontSize: '11px', marginBottom: '4px' }}
                                labelFormatter={(label) => new Date(Number(label)).toLocaleDateString()}
                                formatter={(value: number) => [`${value.toFixed(2)} UAH`, 'Balance']}
                              />
                              {activeRange && (
                                <ReferenceArea
                                  x1={activeRange.x1}
                                  x2={activeRange.x2}
                                  strokeOpacity={0}
                                  fill="#ffffff"
                                  fillOpacity={0.25}
                                />
                              )}
                              {activeRange && (
                                <ReferenceLine
                                  x={activeRange.x1}
                                  stroke="#ffffff"
                                  strokeOpacity={0.85}
                                  strokeWidth={2}
                                  strokeDasharray="4 4"
                                />
                              )}
                              {activeRange && (
                                <ReferenceLine
                                  x={activeRange.x2}
                                  stroke="#ffffff"
                                  strokeOpacity={0.85}
                                  strokeWidth={2}
                                  strokeDasharray="4 4"
                                />
                              )}
                              <Line
                                type="monotone"
                                dataKey="balance"
                                stroke="#ffffff"
                                strokeWidth={3}
                                dot={{ r: 0 }}
                                activeDot={{ r: 6, fill: '#ffffff', strokeWidth: 0 }}
                                name="Balance"
                                isAnimationActive={true}
                                animationDuration={1500}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </>
                    )}
                  </div>
                  {summaryData[jar.id] && (
                    <div className="flex flex-wrap gap-2 mt-4 px-1">
                      {summaryData[jar.id].map((m) => (
                        <div
                          key={m.month}
                          onMouseEnter={() => setHoveredMonth({ jarId: jar.id, summary: m, source: 'chip' })}
                          onMouseLeave={() =>
                            setHoveredMonth((prev) => (prev?.source === 'chip' && prev.jarId === jar.id ? null : prev))
                          }
                          className={`
                          px-3 py-1.5 rounded-lg text-xs font-medium cursor-default transition-colors border
                          ${hoveredMonth?.jarId === jar.id && hoveredMonth.summary.month === m.month
                              ? 'bg-white text-black border-white'
                              : 'bg-white/5 text-zinc-400 border-white/5 hover:bg-white/10 hover:text-zinc-200'}
                        `}
                        >
                          {m.month}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default Charts;
