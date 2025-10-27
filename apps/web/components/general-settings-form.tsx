'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '@/lib/query-keys';
import { updateProfile } from '@/lib/services';
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
import { updateProfileSchema } from '@taboot/utils/schemas';
import { UpdateProfileFormValues } from '@taboot/utils/types';
import { Mail, User } from 'lucide-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';

interface GeneralSettingsFormProps {
  user: {
    id: string;
    name: string | null;
    email: string;
  };
  onSuccess?: () => void;
}

export function GeneralSettingsForm({ user, onSuccess }: GeneralSettingsFormProps) {
  const queryClient = useQueryClient();
  const form = useForm<UpdateProfileFormValues>({
    resolver: zodResolver(updateProfileSchema),
    defaultValues: {
      name: '',
      email: '',
    },
  });

  // Update form values when user data is loaded
  useEffect(() => {
    if (user) {
      form.reset({
        name: user.name ?? '',
        email: user.email,
      });
    }
  }, [user, form.reset]);

  const updateProfileMutation = useMutation({
    mutationFn: async (values: UpdateProfileFormValues) => {
      return updateProfile(user.id, user, values);
    },
    onSuccess: (result) => {
      // Invalidate auth-related queries when profile is updated
      // This ensures any cached user data is refreshed
      void queryClient.invalidateQueries({ queryKey: queryKeys.auth.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.user.profile(user.id) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.user.settings() });

      // Show specific message based on what changed
      if (result.emailChanged && result.nameChanged) {
        toast.success('Profile updated successfully!', { duration: 5000 });
      } else if (result.emailChanged) {
        toast.success(
          'Verification email sent! Please check your current email to approve the change.',
          { duration: 5000 },
        );
      } else if (result.nameChanged) {
        toast.success('Profile updated successfully!');
      } else {
        toast.info('No changes were made to your profile.');
      }
      onSuccess?.();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update profile');
    },
  });

  function onSubmit(values: UpdateProfileFormValues) {
    updateProfileMutation.mutate(values);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5" />
          Profile Information
        </CardTitle>
        <CardDescription>
          Update your name and email address. If you change your email, you&apos;ll need to verify
          it again.
        </CardDescription>
      </CardHeader>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Name <span className="text-primary">*</span>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <User className="text-muted-foreground absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform" />
                      <Input
                        placeholder="Enter your name"
                        autoComplete="name"
                        className="pl-10"
                        {...field}
                      />
                    </div>
                  </FormControl>
                  <FormDescription>
                    This is the name that will be displayed on your profile.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Email <span className="text-primary">*</span>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Mail className="text-muted-foreground absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transform" />
                      <Input
                        type="email"
                        inputMode="email"
                        placeholder="Enter your email"
                        autoComplete="email"
                        className="pl-10"
                        {...field}
                      />
                    </div>
                  </FormControl>
                  <FormDescription className="w-full">
                    <span className="block">
                      Your email address is used for signing in and receiving notifications.
                    </span>
                    <span className="text-primary mt-2 block">
                      Changing your email will require verification. A confirmation link will be
                      sent to your current email address.
                    </span>
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
          <CardFooter className="mt-4">
            <Button
              type="submit"
              disabled={updateProfileMutation.isPending || !form.formState.isDirty}
              className="w-full"
            >
              {updateProfileMutation.isPending ? (
                <>
                  <Spinner />
                  Updating profile...
                </>
              ) : (
                'Update Profile'
              )}
            </Button>
          </CardFooter>
        </form>
      </Form>
    </Card>
  );
}
