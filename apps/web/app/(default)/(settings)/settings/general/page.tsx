import { GeneralSettingsForm } from '@/components/general-settings-form';
import { requireServerSession } from '@/lib/auth-server';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@taboot/ui/components/card';
import { formatDate } from '@taboot/utils';

export default async function GeneralSettingsPage() {
  const session = await requireServerSession();
  const user = session.user;

  return (
    <section className="mx-auto max-w-xl space-y-6 px-4 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">General Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account information and personal details.
        </p>
      </div>

      <GeneralSettingsForm user={user} />

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
