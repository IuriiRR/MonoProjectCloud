import { auth } from './firebase';

const USERS_API_URL = import.meta.env.VITE_USERS_API_URL || 'http://localhost:8081';
const ACCOUNTS_API_URL = import.meta.env.VITE_ACCOUNTS_API_URL || 'http://localhost:8082';
const TRANSACTIONS_API_URL = import.meta.env.VITE_TRANSACTIONS_API_URL || 'http://localhost:8083';
const REPORT_API_URL = import.meta.env.VITE_REPORT_API_URL || 'http://localhost:8086';

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const user = auth.currentUser;
  if (!user) return {};
  const token = await user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

async function apiFetchJson(url: string, init?: RequestInit): Promise<any> {
  const authHeaders = await getAuthHeaders();
  const headers = {
    ...(init?.headers || {}),
    ...authHeaders,
  } as Record<string, string>;

  const resp = await fetch(url, { ...init, headers });

  let payload: any = null;
  const contentType = resp.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    payload = await resp.json().catch(() => null);
  } else {
    payload = await resp.text().catch(() => null);
  }

  if (!resp.ok) {
    const message =
      (payload && typeof payload === 'object' && (payload.error || payload.message)) ||
      `Request failed (${resp.status})`;
    const code = payload && typeof payload === 'object' ? payload.code : undefined;
    const details = payload && typeof payload === 'object' ? payload.details : undefined;
    throw new ApiError(String(message), resp.status, code, details);
  }

  return payload;
}

export interface UserProfile {
  user_id: string;
  username?: string;
  mono_token?: string;
  active: boolean;
  telegram_id?: number | null;
  daily_report?: boolean;
  family_members?: string[];
}

export interface FamilyRequest {
  requester_id: string;
  requester_name?: string;
  status: string;
  created_at?: any;
}

export interface FamilyMemberInfo {
  user_id: string;
  username?: string | null;
  active?: boolean | null;
}

export interface Account {
  id: string;
  type: string;
  currency: any;
  balance: number;
  title?: string;
  is_budget?: boolean;
  is_active?: boolean;
  goal?: number | null;
  invested?: number;
  ownerId?: string;
}

export interface Transaction {
  id: string;
  time: number;
  description: string;
  amount: number;
  balance: number;
}

export interface DailySpendCoverage {
  tx_id: string;
  covered: boolean;
  covered_cents: number;
  uncovered_cents: number;
  sources: Array<{ tx_id: string; amount_cents: number }>;
  reason?: string | null;
}

export interface DailyReportResponse {
  user_id: string;
  date: string;
  timezone: string;
  totals: { spend_total: number; earn_total: number; net: number };
  spends: DailySpendCoverage[];
  report_markdown: string;
  report_html?: string | null;
}

export interface AccountUpdate {
  type?: string;
  send_id?: string | null;
  currency?: any;
  balance?: number;
  is_active?: boolean;
  title?: string | null;
  goal?: number | null;
  is_budget?: boolean;
  invested?: number;
}

type AccountsCacheEntry = {
  fetchedAt: number;
  accounts: Account[];
};

const ACCOUNTS_CACHE_TTL_MS = 30_000;
const accountsCache = new Map<string, AccountsCacheEntry>();

export function clearAccountsCache(userId?: string) {
  if (!userId) {
    accountsCache.clear();
    return;
  }
  accountsCache.delete(userId);
}

export const fetchUserProfile = async (userId: string): Promise<UserProfile> => {
  const data = await apiFetchJson(`${USERS_API_URL}/users/${userId}`);
  return data.user as UserProfile;
};

export const createUserProfile = async (userId: string, username?: string): Promise<UserProfile> => {
  try {
    const data = await apiFetchJson(`${USERS_API_URL}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, username }),
    });
    return data.user as UserProfile;
  } catch (e: any) {
    if (e instanceof ApiError && e.status === 409) {
      // User already exists, fetch it
      return fetchUserProfile(userId);
    }
    throw e;
  }
};

export const updateUserProfile = async (userId: string, updates: Partial<UserProfile>): Promise<UserProfile> => {
  const data = await apiFetchJson(`${USERS_API_URL}/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  return data.user as UserProfile;
};

export type TelegramConnectInit = { bot_url: string; expires_at?: string };

export const initTelegramConnect = async (userId: string): Promise<TelegramConnectInit> => {
  return (await apiFetchJson(`${USERS_API_URL}/users/${userId}/telegram/connect/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })) as TelegramConnectInit;
};

export const sendDailyReportToTelegram = async (
  userId: string,
  opts?: { date?: string; tz?: string; llm?: boolean }
): Promise<{ sent: boolean }> => {
  return (await apiFetchJson(`${USERS_API_URL}/users/${userId}/telegram/reports/daily/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date: opts?.date,
      tz: opts?.tz,
      llm: opts?.llm,
    }),
  })) as { sent: boolean };
};

export const fetchAccounts = async (userId: string): Promise<Account[]> => {
  const data = await apiFetchJson(`${ACCOUNTS_API_URL}/users/${userId}/accounts`);
  return data.accounts as Account[];
};

export const fetchAccountsCached = async (
  userId: string,
  opts?: { forceRefresh?: boolean }
): Promise<Account[]> => {
  const forceRefresh = Boolean(opts?.forceRefresh);
  const cached = accountsCache.get(userId);
  const now = Date.now();
  if (!forceRefresh && cached && now - cached.fetchedAt < ACCOUNTS_CACHE_TTL_MS) {
    return cached.accounts;
  }
  const accounts = await fetchAccounts(userId);
  accountsCache.set(userId, { accounts, fetchedAt: now });
  return accounts;
};

function _upsertAccountInCache(userId: string, updated: Account) {
  const cached = accountsCache.get(userId);
  if (!cached) return;
  const next = cached.accounts.map((a) => (a.id === updated.id ? { ...a, ...updated } : a));
  accountsCache.set(userId, { accounts: next, fetchedAt: cached.fetchedAt });
}

export const createAccount = async (userId: string, account: any): Promise<Account> => {
  const data = await apiFetchJson(`${ACCOUNTS_API_URL}/users/${userId}/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(account),
  });
  return data.account as Account;
};

export const updateAccount = async (
  userId: string,
  accountId: string,
  updates: AccountUpdate
): Promise<Account> => {
  const data = await apiFetchJson(`${ACCOUNTS_API_URL}/users/${userId}/accounts/${accountId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  const account = data.account as Account;
  _upsertAccountInCache(userId, account);
  return account;
};

export const fetchTransactions = async (userId: string, accountId: string): Promise<Transaction[]> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/accounts/${accountId}/transactions?limit=20`);
  return data.transactions as Transaction[];
};

export const fetchAllUserTransactions = async (userId: string): Promise<Transaction[]> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/transactions`);
  return data.transactions as Transaction[];
};

export const fetchBalanceChartData = async (userId: string): Promise<Record<string, { time: number, balance: number }[]>> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/charts/balance`);
  return data.charts as Record<string, { time: number, balance: number }[]>;
};

export interface MonthlySummary {
  month: string;
  start_balance: number;
  end_balance: number;
  budget: number;
  spent: number;
}

export const fetchMonthlySummary = async (userId: string): Promise<Record<string, MonthlySummary[]>> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/charts/monthly_summary`);
  return data.summary as Record<string, MonthlySummary[]>;
};

export const fetchDailyReport = async (
  userId: string,
  opts?: { date?: string; tz?: string; llm?: boolean }
): Promise<DailyReportResponse> => {
  const qs = new URLSearchParams();
  if (opts?.date) qs.set('date', opts.date);
  if (opts?.tz) qs.set('tz', opts.tz);
  if (opts?.llm === false) qs.set('llm', '0');
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return (await apiFetchJson(`${REPORT_API_URL}/users/${userId}/reports/daily${suffix}`)) as DailyReportResponse;
};

export const generateFamilyInviteCode = async (userId: string): Promise<{ code: string; expires_at: string }> => {
  return await apiFetchJson(`${USERS_API_URL}/users/${userId}/family/invite`, {
    method: 'POST',
  });
};

export const joinFamily = async (userId: string, code: string): Promise<{ status: string; target_user_id: string }> => {
  return await apiFetchJson(`${USERS_API_URL}/users/${userId}/family/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
};

export const fetchFamilyRequests = async (userId: string): Promise<FamilyRequest[]> => {
  const data = await apiFetchJson(`${USERS_API_URL}/users/${userId}/family/requests`);
  return data.requests as FamilyRequest[];
};

export const respondToFamilyRequest = async (userId: string, requesterId: string, action: 'accept' | 'reject'): Promise<void> => {
  await apiFetchJson(`${USERS_API_URL}/users/${userId}/family/requests/${requesterId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
};

export const removeFamilyMember = async (userId: string, memberId: string): Promise<void> => {
  await apiFetchJson(`${USERS_API_URL}/users/${userId}/family/members/${memberId}`, {
    method: 'DELETE',
  });
};

export const fetchFamilyMembers = async (userId: string): Promise<FamilyMemberInfo[]> => {
  const data = await apiFetchJson(`${USERS_API_URL}/users/${userId}/family/members`);
  return (data.members || []) as FamilyMemberInfo[];
};
