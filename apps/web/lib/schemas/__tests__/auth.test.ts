import { describe, expect, test } from 'vitest';
import {
  hasPasswordResponseSchema,
  setPasswordRequestSchema,
  setPasswordResponseSchema,
  changePasswordRequestSchema,
  changePasswordResponseSchema,
  signInRequestSchema,
  signInResponseSchema,
  signUpRequestSchema,
  signUpResponseSchema,
  forgotPasswordRequestSchema,
  forgotPasswordResponseSchema,
  resetPasswordRequestSchema,
  resetPasswordResponseSchema,
  sessionResponseSchema,
  errorResponseSchema,
  validationErrorResponseSchema,
  passwordSchema,
  emailSchema,
} from '../auth';

describe('Auth Schemas', () => {
  describe('passwordSchema', () => {
    test('accepts valid passwords', () => {
      expect(passwordSchema.parse('password123')).toBe('password123');
      expect(passwordSchema.parse('12345678')).toBe('12345678');
      expect(passwordSchema.parse('a'.repeat(100))).toBe('a'.repeat(100));
    });

    test('rejects passwords shorter than 8 characters', () => {
      expect(() => passwordSchema.parse('short')).toThrow();
      expect(() => passwordSchema.parse('1234567')).toThrow();
    });

    test('rejects passwords longer than 100 characters', () => {
      expect(() => passwordSchema.parse('a'.repeat(101))).toThrow();
    });

    test('rejects non-string passwords', () => {
      expect(() => passwordSchema.parse(12345678)).toThrow();
      expect(() => passwordSchema.parse(null)).toThrow();
      expect(() => passwordSchema.parse(undefined)).toThrow();
    });
  });

  describe('emailSchema', () => {
    test('accepts valid email addresses', () => {
      expect(emailSchema.parse('test@example.com')).toBe('test@example.com');
      expect(emailSchema.parse('user.name+tag@example.co.uk')).toBe(
        'user.name+tag@example.co.uk',
      );
    });

    test('rejects invalid email addresses', () => {
      expect(() => emailSchema.parse('not-an-email')).toThrow();
      expect(() => emailSchema.parse('missing@domain')).toThrow();
      expect(() => emailSchema.parse('@example.com')).toThrow();
      expect(() => emailSchema.parse('user@')).toThrow();
    });
  });

  describe('hasPasswordResponseSchema', () => {
    test('accepts valid response', () => {
      const result = hasPasswordResponseSchema.parse({ hasPassword: true });
      expect(result).toEqual({ hasPassword: true });
    });

    test('rejects invalid response', () => {
      expect(() => hasPasswordResponseSchema.parse({ hasPassword: 'yes' })).toThrow();
      expect(() => hasPasswordResponseSchema.parse({})).toThrow();
      expect(() => hasPasswordResponseSchema.parse({ wrong: true })).toThrow();
    });
  });

  describe('setPasswordRequestSchema', () => {
    test('accepts valid request', () => {
      const result = setPasswordRequestSchema.parse({ newPassword: 'password123' });
      expect(result).toEqual({ newPassword: 'password123' });
    });

    test('rejects invalid passwords', () => {
      expect(() => setPasswordRequestSchema.parse({ newPassword: 'short' })).toThrow();
      expect(() => setPasswordRequestSchema.parse({ newPassword: 'a'.repeat(101) })).toThrow();
      expect(() => setPasswordRequestSchema.parse({})).toThrow();
    });
  });

  describe('changePasswordRequestSchema', () => {
    test('accepts valid request', () => {
      const result = changePasswordRequestSchema.parse({
        currentPassword: 'oldpassword',
        newPassword: 'newpassword',
      });
      expect(result).toEqual({
        currentPassword: 'oldpassword',
        newPassword: 'newpassword',
      });
    });

    test('rejects missing fields', () => {
      expect(() => changePasswordRequestSchema.parse({ currentPassword: 'password' })).toThrow();
      expect(() => changePasswordRequestSchema.parse({ newPassword: 'password' })).toThrow();
    });

    test('strips unknown fields from request (security)', () => {
      const result = changePasswordRequestSchema.parse({
        currentPassword: 'oldpassword',
        newPassword: 'newpassword',
        // @ts-expect-error - testing runtime behavior
        userId: 'malicious-user-id',
        // @ts-expect-error - testing runtime behavior
        isAdmin: true,
      });
      // Unknown fields are stripped to prevent injection attacks
      expect(result).not.toHaveProperty('userId');
      expect(result).not.toHaveProperty('isAdmin');
      expect(result).toEqual({
        currentPassword: 'oldpassword',
        newPassword: 'newpassword',
      });
    });
  });

  describe('signInRequestSchema', () => {
    test('accepts valid sign-in request', () => {
      const result = signInRequestSchema.parse({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(result).toEqual({
        email: 'test@example.com',
        password: 'password123',
      });
    });

    test('accepts optional rememberMe field', () => {
      const result = signInRequestSchema.parse({
        email: 'test@example.com',
        password: 'password123',
        rememberMe: true,
      });
      expect(result.rememberMe).toBe(true);
    });

    test('rejects invalid email', () => {
      expect(() =>
        signInRequestSchema.parse({
          email: 'not-an-email',
          password: 'password123',
        }),
      ).toThrow();
    });

    test('rejects invalid password', () => {
      expect(() =>
        signInRequestSchema.parse({
          email: 'test@example.com',
          password: 'short',
        }),
      ).toThrow();
    });
  });

  describe('signInResponseSchema', () => {
    test('accepts valid sign-in response', () => {
      const result = signInResponseSchema.parse({
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          image: 'https://example.com/image.jpg',
        },
        session: {
          id: 'session-123',
          expiresAt: '2025-10-25T12:00:00Z',
        },
      });
      expect(result.user.id).toBe('123');
      expect(result.session.id).toBe('session-123');
    });

    test('accepts null name and image', () => {
      const result = signInResponseSchema.parse({
        user: {
          id: '123',
          email: 'test@example.com',
          name: null,
          image: null,
        },
        session: {
          id: 'session-123',
          expiresAt: '2025-10-25T12:00:00Z',
        },
      });
      expect(result.user.name).toBeNull();
      expect(result.user.image).toBeNull();
    });

    test('rejects invalid datetime', () => {
      expect(() =>
        signInResponseSchema.parse({
          user: {
            id: '123',
            email: 'test@example.com',
            name: null,
            image: null,
          },
          session: {
            id: 'session-123',
            expiresAt: 'not-a-datetime',
          },
        }),
      ).toThrow();
    });

    test('strips extraneous fields (Zod default behavior)', () => {
      const result = signInResponseSchema.parse({
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          image: 'https://example.com/image.jpg',
          // @ts-expect-error - testing runtime behavior with unknown fields
          extraField: 'should be stripped',
        },
        session: {
          id: 'session-123',
          expiresAt: '2025-10-25T12:00:00Z',
          // @ts-expect-error - testing runtime behavior with unknown fields
          anotherExtra: 'also stripped',
        },
        // @ts-expect-error - testing runtime behavior with unknown fields
        unknownTopLevel: 'stripped',
      });
      // Zod strips unknown fields by default (strip mode)
      expect(result).not.toHaveProperty('unknownTopLevel');
      expect(result.user).not.toHaveProperty('extraField');
      expect(result.session).not.toHaveProperty('anotherExtra');
      expect(result).toEqual({
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          image: 'https://example.com/image.jpg',
        },
        session: {
          id: 'session-123',
          expiresAt: '2025-10-25T12:00:00Z',
        },
      });
    });
  });

  describe('signUpRequestSchema', () => {
    test('accepts valid sign-up request', () => {
      const result = signUpRequestSchema.parse({
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User',
      });
      expect(result).toEqual({
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User',
      });
    });

    test('accepts request without name', () => {
      const result = signUpRequestSchema.parse({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(result.name).toBeUndefined();
    });

    test('rejects empty name', () => {
      expect(() =>
        signUpRequestSchema.parse({
          email: 'test@example.com',
          password: 'password123',
          name: '',
        }),
      ).toThrow();
    });

    test('rejects name longer than 100 characters', () => {
      expect(() =>
        signUpRequestSchema.parse({
          email: 'test@example.com',
          password: 'password123',
          name: 'a'.repeat(101),
        }),
      ).toThrow();
    });
  });

  describe('forgotPasswordRequestSchema', () => {
    test('accepts valid email', () => {
      const result = forgotPasswordRequestSchema.parse({ email: 'test@example.com' });
      expect(result).toEqual({ email: 'test@example.com' });
    });

    test('rejects invalid email', () => {
      expect(() => forgotPasswordRequestSchema.parse({ email: 'not-an-email' })).toThrow();
    });
  });

  describe('resetPasswordRequestSchema', () => {
    test('accepts valid reset request', () => {
      const result = resetPasswordRequestSchema.parse({
        token: 'valid-token-123',
        newPassword: 'newpassword123',
      });
      expect(result).toEqual({
        token: 'valid-token-123',
        newPassword: 'newpassword123',
      });
    });

    test('rejects empty token', () => {
      expect(() =>
        resetPasswordRequestSchema.parse({
          token: '',
          newPassword: 'newpassword123',
        }),
      ).toThrow();
    });

    test('rejects invalid password', () => {
      expect(() =>
        resetPasswordRequestSchema.parse({
          token: 'valid-token-123',
          newPassword: 'short',
        }),
      ).toThrow();
    });
  });

  describe('sessionResponseSchema', () => {
    test('accepts valid session response', () => {
      const result = sessionResponseSchema.parse({
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          image: 'https://example.com/image.jpg',
        },
        session: {
          id: 'session-123',
          expiresAt: '2025-10-25T12:00:00Z',
        },
      });
      expect(result.user.id).toBe('123');
      expect(result.session.id).toBe('session-123');
    });

    test('strips extraneous fields from session response', () => {
      const result = sessionResponseSchema.parse({
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          image: 'https://example.com/image.jpg',
          // @ts-expect-error - testing runtime behavior
          internalField: 'stripped',
        },
        session: {
          id: 'session-123',
          expiresAt: '2025-10-25T12:00:00Z',
        },
      });
      expect(result.user).not.toHaveProperty('internalField');
    });
  });

  describe('errorResponseSchema', () => {
    test('accepts valid error response', () => {
      const result = errorResponseSchema.parse({ error: 'Something went wrong' });
      expect(result).toEqual({ error: 'Something went wrong' });
    });

    test('rejects non-string error', () => {
      expect(() => errorResponseSchema.parse({ error: 123 })).toThrow();
    });
  });

  describe('validationErrorResponseSchema', () => {
    test('accepts error with details', () => {
      const result = validationErrorResponseSchema.parse({
        error: 'Validation failed',
        details: [
          { field: 'email', message: 'Invalid email' },
          { field: 'password', message: 'Too short' },
        ],
      });
      expect(result.details).toHaveLength(2);
    });

    test('accepts error without details', () => {
      const result = validationErrorResponseSchema.parse({
        error: 'Validation failed',
      });
      expect(result.details).toBeUndefined();
    });

    test('rejects invalid details structure', () => {
      expect(() =>
        validationErrorResponseSchema.parse({
          error: 'Validation failed',
          details: [{ wrong: 'structure' }],
        }),
      ).toThrow();
    });
  });

  describe('Response schemas', () => {
    test('setPasswordResponseSchema accepts valid response', () => {
      const result = setPasswordResponseSchema.parse({ message: 'Password set successfully' });
      expect(result.message).toBe('Password set successfully');
    });

    test('changePasswordResponseSchema accepts valid response', () => {
      const result = changePasswordResponseSchema.parse({
        message: 'Password changed successfully',
      });
      expect(result.message).toBe('Password changed successfully');
    });

    test('signUpResponseSchema accepts valid response', () => {
      const result = signUpResponseSchema.parse({
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
        message: 'User created successfully',
      });
      expect(result.user.id).toBe('123');
      expect(result.message).toBe('User created successfully');
    });

    test('forgotPasswordResponseSchema accepts valid response', () => {
      const result = forgotPasswordResponseSchema.parse({
        message: 'Reset email sent',
      });
      expect(result.message).toBe('Reset email sent');
    });

    test('resetPasswordResponseSchema accepts valid response', () => {
      const result = resetPasswordResponseSchema.parse({
        message: 'Password reset successfully',
      });
      expect(result.message).toBe('Password reset successfully');
    });
  });
});
