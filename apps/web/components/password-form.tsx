'use client';

import { useHasPassword } from '@/hooks/use-has-password';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { changePassword } from '@taboot/auth/client';
import { Button } from '@taboot/ui/components/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@taboot/ui/components/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@taboot/ui/components/form';
import { Input } from '@taboot/ui/components/input';
import { Spinner } from '@taboot/ui/components/spinner';
import { changePasswordSchema, setPasswordSchema } from '@taboot/utils/schemas';
import { ChangePasswordFormValues, SetPasswordFormValues } from '@taboot/utils/types';
import { Eye, EyeOff, Lock } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';

interface PasswordFormProps {
  onSuccess?: () => void;
}

export function PasswordForm({ onSuccess }: PasswordFormProps) {
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const { data: hasPassword, isLoading: isCheckingPassword } = useHasPassword();
  const isChangeMode = hasPassword === true;

  const form = useForm<SetPasswordFormValues | ChangePasswordFormValues>({
    resolver: zodResolver(isChangeMode ? changePasswordSchema : setPasswordSchema),
    defaultValues: {
      currentPassword: '',
      password: '',
      confirmPassword: '',
    },
  });

  const setPasswordMutation = useMutation({
    mutationFn: async (values: SetPasswordFormValues) => {
      const body = { newPassword: values.password };
      const baseUrl = (process.env.NEXT_PUBLIC_BASE_URL ?? '').replace(/\/$/, '');
      const response = await fetch(`${baseUrl}/api/auth/password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const errorMessage =
          (payload as { error?: string; message?: string } | null)?.error ??
          (payload as { error?: string; message?: string } | null)?.message ??
          `Failed to set password (${response.status})`;
        throw new Error(errorMessage);
      }

      return payload;
    },
    onSuccess: () => {
      toast.success(`Password set successfully!`);
      form.reset();
      onSuccess?.();
    },
    onError: (error: Error) => {
      console.error(`Error setting password:`, error);
      toast.error(error.message || `Failed to set password`);
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: async (values: ChangePasswordFormValues) => {
      const result = await changePassword({
        currentPassword: values.currentPassword,
        newPassword: values.password,
      });
      return result;
    },
    onSuccess: () => {
      toast.success('Password changed successfully!');
      form.reset();
      onSuccess?.();
    },
    onError: (error: Error) => {
      console.error('Error changing password:', error);
      toast.error(error.message || 'Failed to change password');
    },
  });

  function onSubmit(values: SetPasswordFormValues | ChangePasswordFormValues) {
    if (isChangeMode) {
      changePasswordMutation.mutate(values as ChangePasswordFormValues);
    } else {
      setPasswordMutation.mutate(values);
    }
  }

  if (isCheckingPassword) {
    return (
      <Card id="set-password" className="scroll-mt-6">
        <CardContent className="flex items-center justify-center py-12">
          <Spinner />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card id="set-password" className="scroll-mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="h-5 w-5" />
          {isChangeMode ? 'Change Password' : 'Set Account Password'}
        </CardTitle>
        <CardDescription>
          {isChangeMode
            ? 'Update your account password. Make sure to choose a strong password.'
            : 'Set a password for your account to enable additional security features like two-factor authentication.'}
        </CardDescription>
      </CardHeader>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {isChangeMode && (
              <FormField
                control={form.control}
                name="currentPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Current Password <span className="text-primary">*</span>
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="text-muted-foreground absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform" />
                        <Input
                          type={showCurrentPassword ? 'text' : 'password'}
                          placeholder="Enter current password"
                          autoComplete="current-password"
                          className="pl-10"
                          {...field}
                        />
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="text-muted-foreground hover:text-muted-foreground absolute right-0 top-1/2 -translate-y-1/2 transform"
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        >
                          {showCurrentPassword ? (
                            <EyeOff className="h-5 w-5" />
                          ) : (
                            <Eye className="h-5 w-5" />
                          )}
                        </Button>
                      </div>
                    </FormControl>
                    <FormDescription>
                      Enter your current password to confirm it&apos;s you.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {isChangeMode ? 'New Password' : 'Password'}{' '}
                    <span className="text-primary">*</span>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Lock className="text-muted-foreground absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform" />
                      <Input
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Minimum 8 characters"
                        autoComplete="new-password"
                        className="pl-10"
                        {...field}
                      />
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        className="text-muted-foreground hover:text-muted-foreground absolute right-0 top-1/2 -translate-y-1/2 transform"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeOff className="h-5 w-5" />
                        ) : (
                          <Eye className="h-5 w-5" />
                        )}
                      </Button>
                    </div>
                  </FormControl>
                  <FormDescription>
                    Choose a strong password with at least 8 characters.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="confirmPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Confirm Password <span className="text-primary">*</span>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Lock className="text-muted-foreground absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform" />
                      <Input
                        type={showConfirmPassword ? 'text' : 'password'}
                        placeholder="Re-enter your password"
                        autoComplete="new-password"
                        className="pl-10"
                        {...field}
                      />
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        className="text-muted-foreground hover:text-muted-foreground absolute right-0 top-1/2 -translate-y-1/2 transform"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="h-5 w-5" />
                        ) : (
                          <Eye className="h-5 w-5" />
                        )}
                      </Button>
                    </div>
                  </FormControl>
                  <FormDescription>Re-enter your password to confirm.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
          <CardFooter className="mt-4">
            <Button
              type="submit"
              disabled={setPasswordMutation.isPending || changePasswordMutation.isPending}
              className="w-full"
            >
              {setPasswordMutation.isPending || changePasswordMutation.isPending ? (
                <>
                  <Spinner />
                  {isChangeMode ? 'Changing password...' : 'Setting password...'}
                </>
              ) : isChangeMode ? (
                'Change Password'
              ) : (
                'Set Password'
              )}
            </Button>
          </CardFooter>
        </form>
      </Form>
    </Card>
  );
}
