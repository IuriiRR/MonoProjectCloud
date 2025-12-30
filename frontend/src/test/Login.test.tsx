import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../pages/Login';
import { describe, it, expect } from 'vitest';

describe('Login Page', () => {
  it('renders login heading', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
    expect(screen.getByRole('heading', { name: /Login/i })).toBeInTheDocument();
  });

  it('does not render email/password inputs', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
    expect(screen.queryByLabelText(/Email/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Password/i)).not.toBeInTheDocument();
  });

  it('renders google login button', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
    expect(screen.getByText(/Google Login/i)).toBeInTheDocument();
  });

  it('shows initial error if provided', () => {
    render(
      <BrowserRouter>
        <Login initialError="User not found, please, register first" />
      </BrowserRouter>
    );
    expect(screen.getByText(/User not found, please, register first/i)).toBeInTheDocument();
  });
});

