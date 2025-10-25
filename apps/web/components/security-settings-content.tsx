'use client';

import { DeleteAccountForm } from '@/components/delete-account-form';
import { PasswordForm } from '@/components/password-form';
import { TwoFactorSetup } from '@/components/two-factor-setup';
import { useHasPassword } from '@/hooks/use-has-password';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@taboot/ui/components/card';
import { Skeleton } from '@taboot/ui/components/skeleton';

interface SecuritySettingsContentProps {
  user: {
    id: string;
    email: string;
    emailVerified: boolean | null;
    twoFactorEnabled: boolean | null | undefined;
  };
}

export function SecuritySettingsContent({ user }: SecuritySettingsContentProps) {
  const { isLoading: checkingPassword, refetch: refetchPasswordStatus } = useHasPassword();

  if (checkingPassword) {
    return (
      <section className="w-xl mx-auto max-w-3xl space-y-6 px-4 py-10">
        <div>
          <Skeleton className="mb-2 h-8 w-48" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </section>
    );
  }

  return (
    <>
      {/* Password management - shows Set Password or Change Password based on user's current state */}
      <PasswordForm onSuccess={() => refetchPasswordStatus()} />

      <TwoFactorSetup isEnabled={user.twoFactorEnabled ?? false} />

      <Card>
        <CardHeader>
          <CardTitle>Account Security</CardTitle>
          <CardDescription>Additional security information about your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-muted-foreground text-sm">Email Verified</p>
            <p className="font-medium">{user.emailVerified ? 'Yes' : 'No'}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-sm">Two-Factor Authentication</p>
            <p className="font-medium">{user.twoFactorEnabled ? 'Enabled' : 'Disabled'}</p>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone - Delete Account */}
      <DeleteAccountForm />
    </>
  );
}
