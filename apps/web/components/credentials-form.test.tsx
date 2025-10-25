import { renderWithProviders, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CredentialsForm } from './credentials-form';

// Mock auth client
vi.mock('@taboot/auth/client', () => ({
  signIn: {
    email: vi.fn(),
  },
  signUp: {
    email: vi.fn(),
  },
  sendVerificationEmail: vi.fn(),
  useSession: vi.fn(() => ({
    data: null,
    isPending: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// Mock next/navigation
const mockPush = vi.fn();
const mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => mockSearchParams,
  usePathname: () => '/sign-in',
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
  },
}));

describe('CredentialsForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Sign In Mode', () => {
    it('should render email and password fields', () => {
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      expect(screen.getByPlaceholderText(/yourname@example.com/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/minimum 8 characters/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('should not render name field in sign-in mode', () => {
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      expect(screen.queryByLabelText(/name/i)).not.toBeInTheDocument();
    });

    it('should allow typing in email field', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const emailInput = screen.getByPlaceholderText(/yourname@example.com/i);
      await user.type(emailInput, 'test@example.com');

      expect(emailInput).toHaveValue('test@example.com');
    });

    it('should allow typing in password field', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const passwordInput = screen.getByPlaceholderText(/minimum 8 characters/i);
      await user.type(passwordInput, 'password123');

      expect(passwordInput).toHaveValue('password123');
    });

    it('should toggle password visibility', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const passwordInput = screen.getByPlaceholderText(/minimum 8 characters/i);
      const toggleButton = screen.getByRole('button', { name: /show password/i });

      expect(passwordInput).toHaveAttribute('type', 'password');

      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'text');

      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('should show forgot password link', () => {
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const forgotPasswordLink = screen.getByRole('link', { name: /forgot password/i });
      expect(forgotPasswordLink).toHaveAttribute('href', '/forgot-password');
    });

    it('should show sign up link', () => {
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const signUpLink = screen.getByRole('link', { name: /sign up/i });
      expect(signUpLink).toHaveAttribute('href', '/sign-up');
    });
  });

  describe('Sign Up Mode', () => {
    it('should render name, email, and password fields', () => {
      renderWithProviders(<CredentialsForm mode="sign-up" />);

      expect(screen.getByPlaceholderText(/your name/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/yourname@example.com/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/minimum 8 characters/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign up/i })).toBeInTheDocument();
    });

    it('should allow typing in name field', async () => {
      const user = userEvent.setup();
      renderWithProviders(<CredentialsForm mode="sign-up" />);

      const nameInput = screen.getByPlaceholderText(/your name/i);
      await user.type(nameInput, 'John Doe');

      expect(nameInput).toHaveValue('John Doe');
    });

    it('should not show forgot password link', () => {
      renderWithProviders(<CredentialsForm mode="sign-up" />);

      expect(screen.queryByRole('link', { name: /forgot password/i })).not.toBeInTheDocument();
    });

    it('should show sign in link', () => {
      renderWithProviders(<CredentialsForm mode="sign-up" />);

      const signInLink = screen.getByRole('link', { name: /sign in/i });
      expect(signInLink).toHaveAttribute('href', '/sign-in');
    });

    it('should show strong password guidance', () => {
      renderWithProviders(<CredentialsForm mode="sign-up" />);

      expect(screen.getByText(/choose a strong password/i)).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('should disable submit button while submitting', async () => {
      const user = userEvent.setup();
      const { signIn } = await import('@taboot/auth/client');

      // Make signIn return a pending promise
      let resolveSignIn: (value: unknown) => void;
      const signInPromise = new Promise((resolve) => {
        resolveSignIn = resolve;
      });
      vi.mocked(signIn.email).mockReturnValue(signInPromise as Promise<never>);

      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const emailInput = screen.getByPlaceholderText(/yourname@example.com/i);
      const passwordInput = screen.getByPlaceholderText(/minimum 8 characters/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
        expect(screen.getByText(/signing in/i)).toBeInTheDocument();
      });

      // Resolve the promise
      resolveSignIn!({ data: {}, error: null });
    });

    it('should have submit button', () => {
      renderWithProviders(<CredentialsForm mode="sign-in" />);

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).not.toBeDisabled();
    });
  });
});
