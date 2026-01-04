import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import Charts from '../pages/Charts';

vi.mock('../services/api', () => {
  return {
    fetchAccountsCached: vi.fn(),
    fetchBalanceChartData: vi.fn(),
    fetchMonthlySummary: vi.fn(),
  };
});

// Recharts doesn't play nicely in jsdom (ResizeObserver/layout). Stub to keep tests focused on filtering.
vi.mock('recharts', () => {
  const Stub = (props: any) => <div data-testid={props['data-testid'] || 'recharts-stub'}>{props.children}</div>;
  const LineChart = (props: any) => (
    <div
      data-testid="LineChart"
      onMouseMove={() =>
        props.onMouseMove?.({
          activePayload: [{ payload: { rawTime: 1696118400, time: 1696118400 * 1000, balance: 100 } }], // 2023-10-01
        })
      }
      onMouseLeave={() => props.onMouseLeave?.()}
    >
      {props.children}
    </div>
  );
  return {
    ResponsiveContainer: Stub,
    LineChart,
    Line: Stub,
    CartesianGrid: Stub,
    Tooltip: Stub,
    XAxis: Stub,
    YAxis: Stub,
    ReferenceArea: Stub,
    ReferenceLine: Stub,
  };
});

import * as api from '../services/api';
const mockedApi = api as unknown as {
  fetchAccountsCached: ReturnType<typeof vi.fn>;
  fetchBalanceChartData: ReturnType<typeof vi.fn>;
  fetchMonthlySummary: ReturnType<typeof vi.fn>;
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
    mockedApi.fetchMonthlySummary.mockResolvedValue({});

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

  it('renders monthly summary for budget jars and shows tooltip on hover', async () => {
    mockedApi.fetchAccountsCached.mockResolvedValue([
      { id: 'jar-budget', type: 'jar', currency: { code: 980 }, balance: 1000, title: 'Budget Jar', is_budget: true },
    ]);
    mockedApi.fetchBalanceChartData.mockResolvedValue({
      'jar-budget': [{ time: 1000000000, balance: 1000 }],
    });
    mockedApi.fetchMonthlySummary.mockResolvedValue({
      'jar-budget': [{
        month: '2023-10',
        start_balance: 100,
        end_balance: 200,
        budget: 50,
        spent: 50
      }]
    });

    const user = { uid: 'u1', displayName: 'Test', email: 't@example.com' } as any;
    render(
      <BrowserRouter>
        <Charts user={user} />
      </BrowserRouter>
    );

    // Wait for data
    expect(await screen.findByText('Budget Jar')).toBeInTheDocument();

    // Check if month strip is present
    const monthEl = screen.getByText('2023-10');
    expect(monthEl).toBeInTheDocument();

    // Hover
    fireEvent.mouseEnter(monthEl);

    // Check for tooltip content
    expect(screen.getByText('2023-10 Summary')).toBeInTheDocument();
    expect(screen.getByText('Start')).toBeInTheDocument();
  });

  it('selects month when hovering a transaction point (chart hover)', async () => {
    mockedApi.fetchAccountsCached.mockResolvedValue([
      { id: 'jar-budget', type: 'jar', currency: { code: 980 }, balance: 1000, title: 'Budget Jar', is_budget: true },
    ]);
    mockedApi.fetchBalanceChartData.mockResolvedValue({
      'jar-budget': [{ time: 1696118400, balance: 1000 }],
    });
    mockedApi.fetchMonthlySummary.mockResolvedValue({
      'jar-budget': [
        {
          month: '2023-10',
          start_balance: 100,
          end_balance: 200,
          budget: 50,
          spent: 50,
        },
      ],
    });

    const user = { uid: 'u1', displayName: 'Test', email: 't@example.com' } as any;
    render(
      <BrowserRouter>
        <Charts user={user} />
      </BrowserRouter>
    );

    expect(await screen.findByText('Budget Jar')).toBeInTheDocument();
    // Initially averages shown
    expect(screen.getByText('6-Month Average')).toBeInTheDocument();

    // Simulate hovering a transaction point: our recharts mock triggers onMouseMove with activePayload
    fireEvent.mouseMove(screen.getByTestId('LineChart'));

    // Month should be selected via chart hover
    expect(screen.getByText('2023-10 Summary')).toBeInTheDocument();
    expect(screen.getByText('Start')).toBeInTheDocument();
  });

  it('renders 6-month average when no month is hovered', async () => {
    mockedApi.fetchAccountsCached.mockResolvedValue([
      { id: 'jar-budget', type: 'jar', currency: { code: 980 }, balance: 1000, title: 'Budget Jar', is_budget: true },
    ]);
    mockedApi.fetchBalanceChartData.mockResolvedValue({
      'jar-budget': [{ time: 1000000000, balance: 1000 }],
    });
    // Return 2 months to calculate average
    mockedApi.fetchMonthlySummary.mockResolvedValue({
      'jar-budget': [
        { month: '2023-10', start_balance: 0, end_balance: 0, budget: 200, spent: 100 },
        { month: '2023-09', start_balance: 0, end_balance: 0, budget: 100, spent: 50 },
      ]
    });

    const user = { uid: 'u1', displayName: 'Test', email: 't@example.com' } as any;
    render(
      <BrowserRouter>
        <Charts user={user} />
      </BrowserRouter>
    );

    expect(await screen.findByText('Budget Jar')).toBeInTheDocument();

    // Check for average header
    expect(screen.getByText('6-Month Average')).toBeInTheDocument();
    expect(screen.getByText('Avg Budget')).toBeInTheDocument();
    
    // Avg Budget: (200 + 100) / 2 = 150
    // Avg Spent: (100 + 50) / 2 = 75
    // Note: The component formats numbers with toFixed(2) and renders "+" for budget
    expect(screen.getByText('+1.50')).toBeInTheDocument(); // 150 / 100 = 1.50
    expect(screen.getByText('0.75')).toBeInTheDocument(); // 75 / 100 = 0.75
  });
});

