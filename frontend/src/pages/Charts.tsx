import { User } from 'firebase/auth';
import { ArrowLeft, BarChart3, Info } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Account, fetchAccounts, fetchBalanceChartData } from '../services/api';

interface ChartsProps {
  user: User;
}

const Charts: React.FC<ChartsProps> = ({ user }) => {
  const [jars, setJars] = useState<Account[]>([]);
  const [chartData, setChartData] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, [user.uid]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [accounts, data] = await Promise.all([
        fetchAccounts(user.uid),
        fetchBalanceChartData(user.uid)
      ]);

      const filteredJars = accounts.filter(acc => acc.type === 'jar');
      setJars(filteredJars);

      // Transform data for recharts
      const transformed: Record<string, any[]> = {};
      Object.entries(data).forEach(([accId, points]) => {
        transformed[accId] = points.map(p => ({
          time: new Date(p.time * 1000).toLocaleDateString(),
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

  if (loading) return <div className="flex items-center justify-center h-screen">Loading charts...</div>;

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
          <h1 className="text-3xl font-bold flex items-center tracking-tight">
            <BarChart3 className="mr-3 text-white" />
            Jar Balance Trends
          </h1>
        </header>

        {error && (
          <div className="p-4 mb-8 text-red-400 bg-red-950/20 border border-red-900/50 rounded-xl">
            {error}
          </div>
        )}

        {jars.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <Info className="mx-auto mb-6 text-zinc-600" size={48} />
            <h2 className="text-2xl font-bold mb-2">No Jars Found</h2>
            <p className="text-zinc-500">Only accounts of type "jar" are shown on this page.</p>
          </div>
        ) : (
          <div className="grid gap-12">
            {jars.map(jar => (
              <div key={jar.id} className="glass-card p-8">
                <div className="mb-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                  <div>
                    <h3 className="text-2xl font-bold tracking-tight">{jar.title || 'Untitled Jar'}</h3>
                    <p className="text-sm text-zinc-500 mt-1 font-mono">{jar.id}</p>
                  </div>
                  <div className="sm:text-right">
                    <p className="text-xs text-zinc-500 uppercase font-bold tracking-widest">Current Balance</p>
                    <p className="text-2xl font-black mt-1">{(jar.balance / 100).toLocaleString()} <span className="text-sm font-light text-zinc-500">UAH</span></p>
                  </div>
                </div>

                <div className="h-96 w-full mt-4 bg-black/40 rounded-xl border border-white/5 p-4">
                  {(!chartData[jar.id] || chartData[jar.id].length === 0) ? (
                    <div className="h-full flex items-center justify-center">
                      <p className="text-zinc-600 text-sm italic">No transaction history found for this jar.</p>
                    </div>
                  ) : (
                    <div id={`chart-${jar.id}`} className="w-full h-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={chartData[jar.id]}
                          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#18181b" />
                          <XAxis
                            dataKey="time"
                            tick={{ fontSize: 11, fill: '#71717a' }}
                            minTickGap={40}
                            axisLine={false}
                            tickLine={false}
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
                            formatter={(value: number) => [`${value.toFixed(2)} UAH`, 'Balance']}
                          />
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
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Charts;
