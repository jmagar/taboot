import { SecuritySettingsContent } from '@/components/security-settings-content';
import { requireServerSession } from '@/lib/auth-server';

export default async function SecurityPage() {
  const session = await requireServerSession();
  const user = session.user;

  return (
    <section className="mx-auto max-w-3xl space-y-6 px-4 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Security Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account security settings and two-factor authentication.
        </p>
      </div>

      <SecuritySettingsContent user={user} />
    </section>
  );
}
