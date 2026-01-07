import { User } from 'firebase/auth';
import { ArrowLeft, Check, Copy, Key, RefreshCcw, Save, Trash2, Users, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FamilyRequest,
  UserProfile,
  fetchFamilyRequests,
  fetchUserProfile,
  generateFamilyInviteCode,
  initTelegramConnect,
  joinFamily,
  removeFamilyMember,
  respondToFamilyRequest,
  sendDailyReportToTelegram,
  updateUserProfile,
} from '../services/api';

interface SettingsProps {
  user: User;
}

const Settings: React.FC<SettingsProps> = ({ user }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [monoToken, setMonoToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tgWorking, setTgWorking] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Family state
  const [familyRequests, setFamilyRequests] = useState<FamilyRequest[]>([]);
  const [inviteCode, setInviteCode] = useState<{ code: string; expires_at: string } | null>(null);
  const [joinCode, setJoinCode] = useState('');
  const [familyLoading, setFamilyLoading] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    loadProfile();
  }, [user.uid]);

  const loadProfile = async () => {
    try {
      const data = await fetchUserProfile(user.uid);
      setProfile(data);
      setMonoToken(data.mono_token || '');

      const reqs = await fetchFamilyRequests(user.uid);
      setFamilyRequests(reqs);
    } catch (err: any) {
      setError('Failed to load profile. Make sure you are registered.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await updateUserProfile(user.uid, { mono_token: monoToken });
      setSuccess('Mono token updated successfully!');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleConnectTelegram = async () => {
    setTgWorking(true);
    setError('');
    setSuccess('');
    try {
      const res = await initTelegramConnect(user.uid);
      window.open(res.bot_url, '_blank', 'noopener,noreferrer');
      setSuccess('Telegram bot opened. In Telegram, press Start, then click “Connect reports monohelper”.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setTgWorking(false);
    }
  };

  const handleDisableTelegramReports = async () => {
    setTgWorking(true);
    setError('');
    setSuccess('');
    try {
      const updated = await updateUserProfile(user.uid, { daily_report: false });
      setProfile(updated);
      setSuccess('Telegram reports disabled.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setTgWorking(false);
    }
  };

  const handleEnableTelegramReports = async () => {
    setTgWorking(true);
    setError('');
    setSuccess('');
    try {
      const updated = await updateUserProfile(user.uid, { daily_report: true });
      setProfile(updated);
      setSuccess('Telegram reports enabled.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setTgWorking(false);
    }
  };

  const handleSendDailyReportToTelegram = async () => {
    setTgWorking(true);
    setError('');
    setSuccess('');
    try {
      await sendDailyReportToTelegram(user.uid);
      setSuccess('Daily report sent to Telegram.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setTgWorking(false);
    }
  };

  const handleGenerateInvite = async () => {
    setFamilyLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await generateFamilyInviteCode(user.uid);
      setInviteCode(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setFamilyLoading(false);
    }
  };

  const handleJoinFamily = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinCode) return;
    setFamilyLoading(true);
    setError('');
    setSuccess('');
    try {
      await joinFamily(user.uid, joinCode);
      setSuccess('Family request sent! Wait for approval.');
      setJoinCode('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setFamilyLoading(false);
    }
  };

  const handleRespondRequest = async (requesterId: string, action: 'accept' | 'reject') => {
    setFamilyLoading(true);
    try {
      await respondToFamilyRequest(user.uid, requesterId, action);
      setSuccess(`Request ${action}ed.`);
      loadProfile();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setFamilyLoading(false);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm('Are you sure you want to remove this family member?')) return;
    setFamilyLoading(true);
    try {
      await removeFamilyMember(user.uid, memberId);
      setSuccess('Member removed.');
      loadProfile();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setFamilyLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>;

  const telegramConnected = Boolean(profile?.telegram_id);
  const telegramReportsEnabled = Boolean(profile?.daily_report);
  const familyMembers = profile?.family_members || [];

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-8 pt-12">
      <button
        onClick={() => navigate('/')}
        className="flex items-center text-zinc-400 hover:text-white mb-12 transition-colors group"
      >
        <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>

      <div className="glass-card p-10">
        <div className="flex items-center mb-8">
          <div className="p-3 bg-white/5 rounded-xl border border-white/10 mr-4">
            <Key className="text-white" size={24} />
          </div>
          <h2 className="text-3xl font-bold tracking-tight">Mono Token</h2>
        </div>

        <p className="text-zinc-500 mb-10 leading-relaxed">
          Enter your Monobank personal API token to sync your accounts and transactions.
          You can get your token at <a href="https://api.monobank.ua/" target="_blank" rel="noopener noreferrer" className="text-white hover:underline underline-offset-4 font-medium">api.monobank.ua</a>.
        </p>

        {error && <div className="p-4 mb-6 text-red-400 bg-red-950/20 border border-red-900/50 rounded-xl">{error}</div>}
        {success && <div className="p-4 mb-6 text-green-400 bg-green-950/20 border border-green-900/50 rounded-xl">{success}</div>}

        <form onSubmit={handleSave} className="space-y-8">
          <div>
            <label htmlFor="monoToken" className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">
              Personal API Token
            </label>
            <input
              id="monoToken"
              type="password"
              value={monoToken}
              onChange={(e) => setMonoToken(e.target.value)}
              placeholder="Paste your token here"
              className="input-field font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center justify-center w-full py-4 btn-primary shadow-glow-white disabled:opacity-50"
          >
            {saving ? (
              <span className="flex items-center">
                <RefreshCcw className="animate-spin mr-2" size={18} />
                Saving...
              </span>
            ) : (
              <>
                <Save size={18} className="mr-2" />
                Save Changes
              </>
            )}
          </button>
        </form>
      </div>

      <div className="glass-card p-10 mt-10">
        <div className="flex items-center mb-8">
          <div className="p-3 bg-white/5 rounded-xl border border-white/10 mr-4">
            <Users className="text-white" size={24} />
          </div>
          <h2 className="text-3xl font-bold tracking-tight">Family Sharing</h2>
        </div>

        <p className="text-zinc-500 mb-8 leading-relaxed">
          Share your account visibility with family members. You will be able to see their accounts and they will see yours.
        </p>

        {/* Family Members List */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4 text-white">Family Members</h3>
          {familyMembers.length === 0 ? (
            <div className="text-zinc-500 text-sm italic">No family members yet.</div>
          ) : (
            <div className="space-y-3">
              {familyMembers.map((mid) => (
                <div key={mid} className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10">
                  <span className="text-white font-mono text-sm">{mid}</span>
                  <button
                    onClick={() => handleRemoveMember(mid)}
                    disabled={familyLoading}
                    className="p-2 text-zinc-400 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Incoming Requests */}
        {familyRequests.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-4 text-white">Incoming Requests</h3>
            <div className="space-y-3">
              {familyRequests.map((req) => (
                <div key={req.requester_id} className="flex items-center justify-between p-4 bg-blue-900/20 rounded-xl border border-blue-800/50">
                  <div>
                    <div className="text-white text-sm font-medium">{req.requester_name || 'Unknown'}</div>
                    <div className="text-zinc-400 text-xs font-mono">{req.requester_id}</div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRespondRequest(req.requester_id, 'accept')}
                      disabled={familyLoading}
                      className="p-2 bg-green-900/30 hover:bg-green-900/50 text-green-400 rounded-lg transition-colors"
                    >
                      <Check size={16} />
                    </button>
                    <button
                      onClick={() => handleRespondRequest(req.requester_id, 'reject')}
                      disabled={familyLoading}
                      className="p-2 bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded-lg transition-colors"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-8 border-t border-white/10">
          {/* Invite */}
          <div>
            <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-4">Invite Member</h3>
            <button
              onClick={handleGenerateInvite}
              disabled={familyLoading}
              className="flex items-center justify-center w-full py-3 px-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors disabled:opacity-50 mb-4"
            >
              Generate Invite Code
            </button>

            {inviteCode && (
              <div className="p-4 bg-black/30 rounded-xl border border-white/10">
                <div className="text-xs text-zinc-500 mb-2">Share this code (expires in 1h):</div>
                <div className="flex items-center justify-between">
                  <code className="text-xl font-mono text-green-400 font-bold tracking-widest">{inviteCode.code}</code>
                  <button
                    onClick={() => navigator.clipboard.writeText(inviteCode.code)}
                    className="text-zinc-400 hover:text-white"
                  >
                    <Copy size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Join */}
          <div>
            <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-4">Join Family</h3>
            <form onSubmit={handleJoinFamily} className="flex gap-2">
              <input
                type="text"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value)}
                placeholder="Enter code"
                className="input-field font-mono text-center uppercase"
                maxLength={6}
              />
              <button
                type="submit"
                disabled={familyLoading || !joinCode}
                className="px-4 py-3 btn-primary shadow-glow-white disabled:opacity-50 whitespace-nowrap"
              >
                Send Request
              </button>
            </form>
          </div>
        </div>

      </div>

      <div className="glass-card p-10 mt-10">
        <div className="flex items-center mb-8">
          <div className="p-3 bg-white/5 rounded-xl border border-white/10 mr-4">
            <Key className="text-white" size={24} />
          </div>
          <h2 className="text-3xl font-bold tracking-tight">Telegram Reports</h2>
        </div>

        <p className="text-zinc-500 mb-8 leading-relaxed">
          Connect the Telegram bot to your account to receive daily reports. You can disable reports any time here.
        </p>

        <div className="space-y-4">
          <div className="text-sm text-zinc-400">
            Status:{' '}
            <span className={telegramConnected ? 'text-green-400' : 'text-zinc-500'}>
              {telegramConnected ? `Connected (${profile?.telegram_id})` : 'Not connected'}
            </span>
            {telegramConnected && (
              <>
                {' '}· Reports:{' '}
                <span className={telegramReportsEnabled ? 'text-green-400' : 'text-zinc-500'}>
                  {telegramReportsEnabled ? 'Enabled' : 'Disabled'}
                </span>
              </>
            )}
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={loadProfile}
              disabled={tgWorking}
              className="flex items-center justify-center py-3 px-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors disabled:opacity-50"
            >
              <RefreshCcw className={tgWorking ? 'animate-spin mr-2' : 'mr-2'} size={18} />
              Refresh status
            </button>

            {!telegramConnected ? (
              <button
                type="button"
                onClick={handleConnectTelegram}
                disabled={tgWorking}
                className="flex-1 flex items-center justify-center py-3 px-4 btn-primary shadow-glow-white disabled:opacity-50"
              >
                Connect Telegram reports
              </button>
            ) : telegramReportsEnabled ? (
              <button
                type="button"
                onClick={handleDisableTelegramReports}
                disabled={tgWorking}
                className="flex-1 flex items-center justify-center py-3 px-4 bg-red-950/20 hover:bg-red-950/30 border border-red-900/50 text-red-300 rounded-xl transition-colors disabled:opacity-50"
              >
                Disable Telegram reports
              </button>
            ) : (
              <button
                type="button"
                onClick={handleEnableTelegramReports}
                disabled={tgWorking}
                className="flex-1 flex items-center justify-center py-3 px-4 btn-primary shadow-glow-white disabled:opacity-50"
              >
                Enable Telegram reports
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={handleSendDailyReportToTelegram}
            disabled={tgWorking || !telegramConnected}
            className="flex items-center justify-center w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors disabled:opacity-50"
          >
            Send daily report to Telegram
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
