'use client';

import { CredentialsForm } from '@/components/credentials-form';
import Google from '@/components/icons/google';
import Logo from '@/components/logo';
import { config } from '@/config/site';
import { useAuthUser } from '@/hooks/use-auth-user';
import { useIsMobile } from '@/hooks/use-mobile';
import { signIn } from '@taboot/auth';
import { Button } from '@taboot/ui/components/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@taboot/ui/components/card';
import { cn } from '@taboot/ui/lib/utils';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect } from 'react';

type AuthFormProps = React.ComponentProps<'div'> & {
  mode: 'sign-in' | 'sign-up';
};

export function AuthForm({ mode, className, ...props }: AuthFormProps) {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || '/';
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthUser();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace('/'); // redirect without adding history entry
    }
  }, [isLoading, isAuthenticated, router]);

  // Don't render anything while checking or redirecting
  if (isLoading || isAuthenticated) return null;

  return (
    <div className={cn(className)}>
      <div
        className={cn(
          'mx-auto flex min-h-svh flex-col items-center justify-center gap-6 p-6 md:p-10 lg:p-12',
        )}
        {...props}
      >
        {!isMobile && (
          <Link href="/">
            <Logo variant="auth-form" />
          </Link>
        )}

        <Card className="mx-auto w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-xl">
              Welcome {mode === 'sign-up' ? `to ${config.name}` : 'back'}
            </CardTitle>
            <CardDescription>
              {mode === 'sign-in' ? 'Sign in' : 'Sign up'} with your GitHub or Google account
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6">
              <div className="flex flex-col gap-4">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => signIn.social({ provider: 'google', callbackURL: callbackUrl })}
                >
                  <Google />
                  {mode === 'sign-in' ? 'Sign in' : 'Sign up'} with Google
                </Button>
              </div>
              <div className="after:border-border relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t">
                <span className="bg-card text-muted-foreground relative z-10 px-2">
                  Or continue with
                </span>
              </div>
            </div>
            <CredentialsForm mode={mode} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
