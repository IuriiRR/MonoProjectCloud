import React, { useEffect, useState } from 'react';
import { User, signOut } from 'firebase/auth';
import { auth } from '../services/firebase';
import { fetchAccountsCached, fetchTransactions, Account, Transaction, updateAccount } from '../services/api';
import { ChevronDown, LogOut, RefreshCcw, Settings as SettingsIcon, BarChart3, WalletCards, PiggyBank, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DashboardProps {
  user: User;
}

type AccountsTab = 'jars' | 'cards';

const Dashboard: React.FC<DashboardProps> = ({ user }) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<AccountsTab>('jars');
  const [savingBudget, setSavingBudget] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadAccounts({ forceRefresh: false });
  }, [user.uid]);

  useEffect(() => {
    if (selectedAccountId) {
      loadTransactions(selectedAccountId);
    }
  }, [selectedAccountId, user.uid]);

  const loadAccounts = async (opts?: { forceRefresh?: boolean }) => {
    try {
      setLoading(true);
      const data = await fetchAccountsCached(user.uid, { forceRefresh: Boolean(opts?.forceRefresh) });
      setAccounts(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const jars = accounts.filter(a => a.type === 'jar');
  const cards = accounts.filter(a => a.type === 'card');
  const visibleAccounts = activeTab === 'jars' ? jars : cards;

  useEffect(() => {
    // Keep selection valid within the active tab.
    if (!selectedAccountId) {
      if (visibleAccounts.length > 0) setSelectedAccountId(visibleAccounts[0].id);
      return;
    }
    const stillVisible = visibleAccounts.some(a => a.id === selectedAccountId);
    if (!stillVisible) {
      if (visibleAccounts.length > 0) {
        setSelectedAccountId(visibleAccounts[0].id);
      } else {
        setSelectedAccountId('');
        setTransactions([]);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, accounts]);

  const loadTransactions = async (accountId: string) => {
    try {
      const data = await fetchTransactions(user.uid, accountId);
      setTransactions(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleLogout = () => signOut(auth);

  const selectedAccount = accounts.find(a => a.id === selectedAccountId);
  const selectedIsBudget = Boolean(selectedAccount?.is_budget);

  const handleToggleBudget = async () => {
    if (!selectedAccount || selectedAccount.type !== 'jar') return;
    setSavingBudget(true);
    setError('');
    try {
      const updated = await updateAccount(user.uid, selectedAccount.id, { is_budget: !selectedIsBudget });
      setAccounts(prev => prev.map(a => (a.id === updated.id ? { ...a, ...updated } : a)));
    } catch (err: any) {
      setError(err.message || 'Failed to update budget flag');
    } finally {
      setSavingBudget(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-8">
      <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-12 gap-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome, {user.displayName || user.email}</h1>
          <p className="text-zinc-500 text-sm mt-1">Manage your Monobank accounts</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center bg-zinc-950 border border-white/10 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('jars')}
              className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all ${
                activeTab === 'jars' ? 'bg-white text-black' : 'text-zinc-300 hover:bg-white/5'
              }`}
              aria-pressed={activeTab === 'jars'}
            >
              <PiggyBank size={18} className="mr-2" />
              Jars
              <span className={`ml-2 text-xs font-bold px-2 py-0.5 rounded-full ${
                activeTab === 'jars' ? 'bg-black/10 text-black' : 'bg-white/10 text-zinc-200'
              }`}>
                {jars.length}
              </span>
            </button>
            <button
              onClick={() => setActiveTab('cards')}
              className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all ${
                activeTab === 'cards' ? 'bg-white text-black' : 'text-zinc-300 hover:bg-white/5'
              }`}
              aria-pressed={activeTab === 'cards'}
            >
              <WalletCards size={18} className="mr-2" />
              Cards
              <span className={`ml-2 text-xs font-bold px-2 py-0.5 rounded-full ${
                activeTab === 'cards' ? 'bg-black/10 text-black' : 'bg-white/10 text-zinc-200'
              }`}>
                {cards.length}
              </span>
            </button>
            <button
              onClick={() => navigate('/charts')}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all text-zinc-300 hover:bg-white/5"
              title="Charts"
            >
              <BarChart3 size={18} className="mr-2" />
              Charts
            </button>
            <button
              onClick={() => navigate('/report')}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all text-zinc-300 hover:bg-white/5"
              title="Daily Report"
            >
              <FileText size={18} className="mr-2" />
              Report
            </button>
          </div>
          <button 
            onClick={() => navigate('/settings')}
            className="flex items-center px-4 py-2 text-sm font-medium bg-zinc-900 border border-white/10 rounded-lg hover:border-white/30 transition-all"
          >
            <SettingsIcon size={18} className="mr-2" />
            Settings
          </button>
          <button 
            onClick={handleLogout}
            className="flex items-center px-4 py-2 text-sm font-medium bg-red-950/30 text-red-400 border border-red-900/50 rounded-lg hover:bg-red-900/50 transition-all"
          >
            <LogOut size={18} className="mr-2" />
            Logout
          </button>
        </div>
      </header>

      {error && (
        <div className="p-4 mb-6 text-red-400 bg-red-950/20 border border-red-900/50 rounded-xl flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError('')} className="font-bold hover:text-red-300">&times;</button>
        </div>
      )}

      <div className="grid gap-8">
        {/* Account Selection Section */}
        <section className="glass-card p-8">
          <div className="flex items-center justify-between gap-4 mb-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">
              {activeTab === 'jars' ? 'Select Jar' : 'Select Card'}
            </label>
            <button
              onClick={() => loadAccounts({ forceRefresh: true })}
              className="flex items-center text-xs font-semibold uppercase tracking-wider text-zinc-500 hover:text-white transition-colors"
              title="Refresh accounts"
            >
              <RefreshCcw size={14} className="mr-2" />
              Refresh
            </button>
          </div>
          <div className="relative">
            <select 
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="block w-full pl-4 pr-10 py-3 bg-zinc-950 border border-white/10 text-white rounded-lg appearance-none focus:outline-none focus:border-white/30 transition-all"
            >
              {loading ? (
                <option>Loading...</option>
              ) : visibleAccounts.length === 0 ? (
                <option>{activeTab === 'jars' ? 'No jars found' : 'No cards found'}</option>
              ) : (
                visibleAccounts.map(acc => (
                  <option key={acc.id} value={acc.id} className="bg-zinc-950">
                    {acc.title || 'Untitled'}{acc.type === 'jar' && acc.is_budget ? ' • Budget' : ''} - {(acc.balance / 100).toFixed(2)}
                  </option>
                ))
              )}
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
              <ChevronDown size={20} className="text-zinc-500" />
            </div>
          </div>
          
          {selectedAccount && (
            <div className="mt-8 pt-8 border-t border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6">
              <div>
                <p className="text-xs text-zinc-500 uppercase font-bold tracking-widest">Account Details</p>
                <p className="text-xl font-bold mt-1">{selectedAccount.title || 'Main Account'}</p>
                <p className="text-sm text-zinc-400 mt-0.5">{selectedAccount.type} • {selectedAccount.id}</p>
                {selectedAccount.type === 'jar' ? (
                  <div className="mt-4 flex items-center gap-3">
                    <label className="flex items-center gap-3 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={selectedIsBudget}
                        onChange={handleToggleBudget}
                        disabled={savingBudget}
                        className="h-4 w-4 accent-white disabled:opacity-50"
                        aria-label="Mark jar as budget"
                      />
                      <span className="text-sm text-zinc-300">Budget jar</span>
                    </label>
                    {savingBudget ? (
                      <span className="text-xs text-zinc-500">Saving…</span>
                    ) : selectedIsBudget ? (
                      <span className="text-xs font-bold uppercase tracking-widest px-2 py-1 rounded-md border border-white/10 bg-white/5 text-zinc-200">
                        Budget
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </div>
              <div className="sm:text-right">
                <p className="text-xs text-zinc-500 uppercase font-bold tracking-widest">Available Balance</p>
                <p className="text-4xl font-black mt-1 tracking-tight">
                  {(selectedAccount.balance / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })} 
                  <span className="text-lg ml-2 font-light text-zinc-500">UAH</span>
                </p>
              </div>
            </div>
          )}
        </section>

        {/* Transactions Section */}
        <section className="glass-card overflow-hidden">
          <div className="p-6 border-b border-white/5 flex justify-between items-center">
            <h3 className="font-bold text-lg tracking-tight">Recent Transactions</h3>
            <button 
              onClick={() => selectedAccountId && loadTransactions(selectedAccountId)}
              className="p-2 text-zinc-500 hover:text-white transition-colors"
              title="Refresh transactions"
            >
              <RefreshCcw size={18} />
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-white/5">
                  <th className="px-6 py-4 text-left text-xs font-bold text-zinc-500 uppercase tracking-widest">Date</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-zinc-500 uppercase tracking-widest">Description</th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-zinc-500 uppercase tracking-widest">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-6 py-12 text-center text-zinc-600 italic">
                      {selectedAccountId ? 'No transactions found for this account.' : 'Please select an account.'}
                    </td>
                  </tr>
                ) : (
                  transactions.map(tx => (
                    <tr key={tx.id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500">
                        {new Date(tx.time * 1000).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-zinc-200">
                        {tx.description}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold ${tx.amount < 0 ? 'text-zinc-200' : 'text-white'}`}>
                        {tx.amount < 0 ? '-' : '+'}
                        {Math.abs(tx.amount / 100).toFixed(2)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;

