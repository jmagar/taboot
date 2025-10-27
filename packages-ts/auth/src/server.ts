import {
  changeEmailSchema,
  getTemplate,
  resetPasswordSchema,
  sendEmail,
  verifyEmailSchema,
} from '@taboot/email';
import {
  changeEmailRateLimiter,
  resetPasswordRateLimiter,
  verifyEmailRateLimiter,
} from '@taboot/rate-limit';
import { betterAuth } from 'better-auth';
import { prismaAdapter } from 'better-auth/adapters/prisma';
import { twoFactor } from 'better-auth/plugins';
import { prisma } from '@taboot/db';
import { logger } from '@taboot/logger';

// The inferred type of 'auth' is too complex to name portably (TS2742).
// This is safe because 'auth' is only used internally in server code, not exported to clients.
// The Session type is properly exported via `typeof auth.$Infer.Session` at line 156.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const auth: any = betterAuth({
  database: prismaAdapter(prisma, {
    provider: 'postgresql',
  }),
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // 5 minutes
    },
  },
  advanced: {
    defaultCookieAttributes: {
      sameSite: 'lax', // CSRF protection: prevents cross-site cookie transmission
      secure: process.env.NODE_ENV === 'production', // HTTPS only in production
      httpOnly: true, // XSS protection: prevents JavaScript access
    },
  },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true,
    sendResetPassword: async ({ user, url }) => {
      const { data, success, error } = resetPasswordSchema.safeParse({
        name: user.name,
        resetUrl: url,
      });
      if (error || !success) {
        throw new Error('Failed to send password reset email');
      }

      const { success: rateLimitSuccess } = await resetPasswordRateLimiter.limit(user.email);
      if (!rateLimitSuccess) {
        logger.warn('Password reset rate limit exceeded', {
          userId: user.id,
          operation: 'password-reset',
        });
        return;
      }

      const emailTemplate = getTemplate('reset-password');
      await sendEmail({
        to: user.email,
        subject: emailTemplate.subject,
        react: emailTemplate.render({
          name: data.name,
          resetUrl: data.resetUrl,
        }),
      });
    },
  },
  emailVerification: {
    sendOnSignUp: true,
    autoSignInAfterVerification: true,
    sendVerificationEmail: async ({ user, url }) => {
      const { data, success, error } = verifyEmailSchema.safeParse({
        email: user.email,
        name: user.name,
        verificationUrl: url,
      });
      if (error || !success) {
        throw new Error('Failed to send verification email');
      }

      const { success: rateLimitSuccess } = await verifyEmailRateLimiter.limit(user.email);
      if (!rateLimitSuccess) {
        logger.warn('Email verification rate limit exceeded', {
          userId: user.id,
          operation: 'send-verification',
        });
        return;
      }

      const emailTemplate = getTemplate('verify-email');
      await sendEmail({
        to: user.email,
        subject: emailTemplate.subject,
        react: emailTemplate.render({
          name: data.name,
          email: data.email,
          verificationUrl: data.verificationUrl,
        }),
      });
    },
  },
  user: {
    changeEmail: {
      enabled: true,
      sendChangeEmailVerification: async ({ user, newEmail, url }) => {
        const { data, success, error } = changeEmailSchema.safeParse({
          currentEmail: user.email,
          newEmail,
          name: user.name,
          verificationUrl: url,
        });
        if (error || !success) {
          throw new Error('Failed to send email change verification');
        }

        const { success: rateLimitSuccess } = await changeEmailRateLimiter.limit(user.email);
        if (!rateLimitSuccess) {
          logger.warn('Email change rate limit exceeded', {
            userId: user.id,
            operation: 'change-email',
          });
          return;
        }

        const emailTemplate = getTemplate('change-email');
        await sendEmail({
          to: user.email, // Send to current email
          subject: emailTemplate.subject,
          react: emailTemplate.render({
            name: data.name,
            currentEmail: data.currentEmail,
            newEmail: data.newEmail,
            verificationUrl: data.verificationUrl,
          }),
        });
      },
    },
    deleteUser: {
      enabled: true,
    },
  },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    },
  },
  plugins: [
    twoFactor({
      issuer: 'Taboot',
    }),
  ],
});

// Export the inferred session type from better-auth
export type Session = typeof auth.$Infer.Session;
