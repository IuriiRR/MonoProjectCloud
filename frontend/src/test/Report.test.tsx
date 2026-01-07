import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Report from '../pages/Report';

vi.mock('../services/api', async () => {
  const actual: any = await vi.importActual('../services/api');
  return {
    ...actual,
    fetchDailyReport: vi.fn(async () => ({
      user_id: 'u1',
      date: '2024-01-01',
      timezone: 'Etc/UTC',
      totals: { spend_total: 11000, earn_total: 10000, net: -1000 },
      spends: [],
      report_markdown: '## Daily transactions report — 2024-01-01 (Etc/UTC)\n\n✅ ok',
      report_html: null,
    })),
  };
});

describe('Report page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders and loads report', async () => {
    render(
      <BrowserRouter>
        <Report user={{ uid: 'u1' } as any} />
      </BrowserRouter>
    );
    expect(screen.getByText('Daily Report')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Daily transactions report/)).toBeInTheDocument();
    });
  });
});

