import { requireServerSession } from '@/lib/auth-server';
import { Skeleton } from '@taboot/ui/components/skeleton';
import { Suspense } from 'react';

async function WelcomeMessage() {
  const session = await requireServerSession();
  const user = session.user;

  return (
    <div className="rounded-md py-4">
      <p>
        <span>Welcome back, </span>
        <span className="font-bold">{user.name || user.email}</span>!
      </p>
    </div>
  );
}

function WelcomeMessageLoading() {
  return (
    <div className="rounded-md py-4">
      <Skeleton className="h-5 w-64" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <section className="max-w-2xl p-12">
      <h1 className="mb-4 text-2xl font-semibold">Dashboard</h1>
      <Suspense fallback={<WelcomeMessageLoading />}>
        <WelcomeMessage />
      </Suspense>
    </section>
  );
}
