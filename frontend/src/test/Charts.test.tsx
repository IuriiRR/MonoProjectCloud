import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import Charts from '../pages/Charts';

vi.mock('../services/api', () => {
  return {
    fetchAccountsCached: vi.fn(),
    fetchBalanceChartData: vi.fn(),
  };
});

// Recharts doesn't play nicely in jsdom (ResizeObserver/layout). Stub to keep tests focused on filtering.
vi.mock('recharts', () => {
  const Stub = (props: any) => <div data-testid={props['data-testid'] || 'recharts-stub'}>{props.children}</div>;
  return {
    ResponsiveContainer: Stub,
    LineChart: Stub,
    Line: Stub,
    CartesianGrid: Stub,
    Tooltip: Stub,
    XAxis: Stub,
    YAxis: Stub,
  };
});

import * as api from '../services/api';
const mockedApi = api as unknown as {
  fetchAccountsCached: ReturnType<typeof vi.fn>;
  fetchBalanceChartData: ReturnType<typeof vi.fn>;
};

describe('Charts', () => {
  it('filters out non-budget jars when Budget only is enabled', async () => {
    mockedApi.fetchAccountsCached.mockResolvedValue([
      { id: 'jar-budget', type: 'jar', currency: { code: 980 }, balance: 1000, title: 'Budget Jar', is_budget: true },
      { id: 'jar-nonbudget', type: 'jar', currency: { code: 980 }, balance: 2000, title: 'Regular Jar', is_budget: false },
      { id: 'card-1', type: 'card', currency: { code: 980 }, balance: 3000, title: 'Card One' },
    ]);
    mockedApi.fetchBalanceChartData.mockResolvedValue({
      'jar-budget': [],
      'jar-nonbudget': [],
    });

    const user = { uid: 'u1', displayName: 'Test', email: 't@example.com' } as any;
    render(
      <BrowserRouter>
        <Charts user={user} />
      </BrowserRouter>
    );

    // Both jars visible by default
    expect(await screen.findByText('Budget Jar')).toBeInTheDocument();
    expect(screen.getByText('Regular Jar')).toBeInTheDocument();

    // Enable Budget only -> non-budget jar disappears
    fireEvent.click(screen.getByLabelText(/Show budget jars only/i));
    expect(screen.getByText('Budget Jar')).toBeInTheDocument();
    expect(screen.queryByText('Regular Jar')).not.toBeInTheDocument();
  });
});

