import { auth } from './firebase';

const USERS_API_URL = import.meta.env.VITE_USERS_API_URL || 'http://localhost:8081';
const ACCOUNTS_API_URL = import.meta.env.VITE_ACCOUNTS_API_URL || 'http://localhost:8082';
const TRANSACTIONS_API_URL = import.meta.env.VITE_TRANSACTIONS_API_URL || 'http://localhost:8083';

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
}

export interface Account {
  id: string;
  type: string;
  currency: any;
  balance: number;
  title?: string;
}

export interface Transaction {
  id: string;
  time: number;
  description: string;
  amount: number;
  balance: number;
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

export const fetchAccounts = async (userId: string): Promise<Account[]> => {
  const data = await apiFetchJson(`${ACCOUNTS_API_URL}/users/${userId}/accounts`);
  return data.accounts as Account[];
};

export const createAccount = async (userId: string, account: any): Promise<Account> => {
  const data = await apiFetchJson(`${ACCOUNTS_API_URL}/users/${userId}/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(account),
  });
  return data.account as Account;
};

export const fetchTransactions = async (userId: string, accountId: string): Promise<Transaction[]> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/accounts/${accountId}/transactions?limit=20`);
  return data.transactions as Transaction[];
};

export const fetchAllUserTransactions = async (userId: string): Promise<Transaction[]> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/transactions`);
  return data.transactions as Transaction[];
};

export const fetchBalanceChartData = async (userId: string): Promise<Record<string, {time: number, balance: number}[]>> => {
  const data = await apiFetchJson(`${TRANSACTIONS_API_URL}/users/${userId}/charts/balance`);
  return data.charts as Record<string, {time: number, balance: number}[]>;
};

