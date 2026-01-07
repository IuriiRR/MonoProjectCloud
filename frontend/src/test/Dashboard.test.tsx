import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from '../pages/Dashboard';

vi.mock('../services/api', () => {
  return {
    fetchAccountsCached: vi.fn(),
    fetchTransactions: vi.fn(),
    updateAccount: vi.fn(),
    fetchFamilyMembers: vi.fn(),
  };
});

import * as api from '../services/api';
const mockedApi = api as unknown as {
  fetchAccountsCached: ReturnType<typeof vi.fn>;
  fetchTransactions: ReturnType<typeof vi.fn>;
  updateAccount: ReturnType<typeof vi.fn>;
  fetchFamilyMembers: ReturnType<typeof vi.fn>;
};

describe('Dashboard', () => {
  beforeEach(() => {
    mockedApi.fetchTransactions.mockResolvedValue([]);
    mockedApi.updateAccount.mockImplementation(async (_userId: string, _accountId: string, updates: any) => {
      return { id: 'jar-1', type: 'jar', currency: { code: 980 }, balance: 1000, title: 'Jar One', ...updates };
    });
    mockedApi.fetchFamilyMembers?.mockResolvedValue([]);
  });

  it('splits jars and cards into tabs (single accounts fetch) and shows budget toggle for jars only', async () => {
    mockedApi.fetchAccountsCached.mockResolvedValue([
      { id: 'jar-1', type: 'jar', currency: { code: 980 }, balance: 1000, title: 'Jar One', is_budget: false },
      { id: 'card-1', type: 'card', currency: { code: 980 }, balance: 2000, title: 'Card One' },
    ]);

    const user = { uid: 'u1', displayName: 'Test', email: 't@example.com' } as any;
    render(
      <BrowserRouter>
        <Dashboard user={user} />
      </BrowserRouter>
    );

    // Jars tab should be active by default and show jar option
    expect(await screen.findByText(/Select Jar/i)).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: /Jar One/i })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Card One/i })).not.toBeInTheDocument();

    // Budget toggle visible for jars
    const budgetToggle = screen.getByLabelText(/Mark jar as budget/i);
    expect(budgetToggle).toBeInTheDocument();

    // Toggle budget -> calls updateAccount
    fireEvent.click(budgetToggle);
    await waitFor(() => {
      expect(mockedApi.updateAccount).toHaveBeenCalledWith('u1', 'jar-1', { is_budget: true });
    });

    // Switch to cards tab -> shows only cards and no budget toggle
    screen.getByRole('button', { name: /Cards/i }).click();
    expect(await screen.findByText(/Select Card/i)).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: /Card One/i })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Jar One/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Mark jar as budget/i)).not.toBeInTheDocument();

    // Ensure we fetched accounts once (cached fetch)
    expect(mockedApi.fetchAccountsCached).toHaveBeenCalledTimes(1);
  });
});

