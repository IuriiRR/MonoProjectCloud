const USERS_API_URL = import.meta.env.VITE_USERS_API_URL || 'http://localhost:8081';
const ACCOUNTS_API_URL = import.meta.env.VITE_ACCOUNTS_API_URL || 'http://localhost:8082';
const TRANSACTIONS_API_URL = import.meta.env.VITE_TRANSACTIONS_API_URL || 'http://localhost:8083';

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
  const response = await fetch(`${USERS_API_URL}/users/${userId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch user profile');
  }
  const data = await response.json();
  return data.user;
};

export const createUserProfile = async (userId: string, username?: string): Promise<UserProfile> => {
  const response = await fetch(`${USERS_API_URL}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, username }),
  });
  if (response.status === 409) {
    // User already exists, fetch it
    return fetchUserProfile(userId);
  }
  if (!response.ok) {
    throw new Error('Failed to create user profile');
  }
  const data = await response.json();
  return data.user;
};

export const updateUserProfile = async (userId: string, updates: Partial<UserProfile>): Promise<UserProfile> => {
  const response = await fetch(`${USERS_API_URL}/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error('Failed to update user profile');
  }
  const data = await response.json();
  return data.user;
};

export const fetchAccounts = async (userId: string): Promise<Account[]> => {
  const response = await fetch(`${ACCOUNTS_API_URL}/users/${userId}/accounts`);
  if (!response.ok) {
    throw new Error('Failed to fetch accounts');
  }
  const data = await response.json();
  return data.accounts;
};

export const createAccount = async (userId: string, account: any): Promise<Account> => {
  const response = await fetch(`${ACCOUNTS_API_URL}/users/${userId}/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(account),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error || 'Failed to create account');
  }
  const data = await response.json();
  return data.account;
};

export const fetchTransactions = async (userId: string, accountId: string): Promise<Transaction[]> => {
  const response = await fetch(`${TRANSACTIONS_API_URL}/users/${userId}/accounts/${accountId}/transactions?limit=20`);
  if (!response.ok) {
    throw new Error('Failed to fetch transactions');
  }
  const data = await response.json();
  return data.transactions;
};

export const fetchAllUserTransactions = async (userId: string): Promise<Transaction[]> => {
  const response = await fetch(`${TRANSACTIONS_API_URL}/users/${userId}/transactions`);
  if (!response.ok) {
    throw new Error('Failed to fetch all transactions');
  }
  const data = await response.json();
  return data.transactions;
};

export const fetchBalanceChartData = async (userId: string): Promise<Record<string, {time: number, balance: number}[]>> => {
  const response = await fetch(`${TRANSACTIONS_API_URL}/users/${userId}/charts/balance`);
  if (!response.ok) {
    throw new Error('Failed to fetch chart data');
  }
  const data = await response.json();
  return data.charts;
};

