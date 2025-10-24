'use client';

import { useRequiredAuthUser } from '@/hooks/use-auth-user';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { changeEmail, updateUser } from '@taboot/auth/client';
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
import { Skeleton } from '@taboot/ui/components/skeleton';
import { Spinner } from '@taboot/ui/components/spinner';
import { formatDate } from '@taboot/utils';
import { updateProfileSchema } from '@taboot/utils/schemas';
import { UpdateProfileFormValues } from '@taboot/utils/types';
import { Mail, User } from 'lucide-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';

export default function GeneralSettingsPage() {
  const { user, isLoading, refetch } = useRequiredAuthUser();

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
        name: user.name,
        email: user.email,
      });
    }
  }, [user, form]);

  const updateProfileMutation = useMutation({
    mutationFn: async (values: UpdateProfileFormValues) => {
      if (!user) throw new Error('User not authenticated');

      const nameChanged = values.name !== user.name;
      const emailChanged = values.email !== user.email;

      if (nameChanged) {
        await updateUser({
          name: values.name,
        });
      }

      if (emailChanged) {
        await changeEmail({
          newEmail: values.email,
          callbackURL: '/settings/general',
        });
      }

      return { nameChanged, emailChanged };
    },
    onSuccess: (result) => {
      if (result.emailChanged) {
        toast.success(
          'Verification email sent! Please check your current email to approve the change.',
          { duration: 5000 },
        );
      } else {
        toast.success('Profile updated successfully!');
      }
      refetch();
    },
    onError: (error: Error) => {
      console.error('Error updating profile:', error);
      toast.error(error.message || 'Failed to update profile');
    },
  });

  function onSubmit(values: UpdateProfileFormValues) {
    updateProfileMutation.mutate(values);
  }

  if (isLoading) {
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
    <section className="mx-auto max-w-xl space-y-6 px-4 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">General Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account information and personal details.
        </p>
      </div>

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

      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Additional details about your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-muted-foreground text-sm">Email Verified</p>
            <p className="font-medium">{user.emailVerified ? 'Yes' : 'No'}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-sm">Account Created</p>
            <p className="font-medium">{formatDate(user.createdAt, 'PPpp')}</p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
