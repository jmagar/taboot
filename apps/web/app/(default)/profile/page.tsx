import { requireServerSession } from '@/lib/auth-server';
import { Avatar, AvatarFallback, AvatarImage } from '@taboot/ui/components/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@taboot/ui/components/card';
import { Skeleton } from '@taboot/ui/components/skeleton';
import { formatDate } from '@taboot/utils';
import { Suspense } from 'react';

async function ProfileCard() {
  const session = await requireServerSession();
  const user = session.user;

  const cardDetails = [
    { label: 'Name', value: user.name || '—' },
    { label: 'User ID', value: user.id },
    { label: 'Email Verified', value: user.emailVerified ? 'Yes' : 'No' },
    { label: 'Profile Image', value: user.image ? 'Available' : 'No image set' },
    { label: 'Created At', value: formatMaybeDate(user.createdAt) },
    { label: 'Updated At', value: formatMaybeDate(user.updatedAt) },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-col items-center justify-center gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          <Avatar className="ring-border h-20 w-20 rounded-md ring-2">
            <AvatarImage
              src={user.image ?? ''}
              alt={user.name ? `${user.name}'s profile photo` : 'User profile photo'}
            />
            <AvatarFallback className="text-3xl capitalize">
              {user.name?.[0] ?? '?'}
            </AvatarFallback>
          </Avatar>
          <div>
            <CardTitle className="text-2xl font-semibold">
              {user.name || 'Unnamed User'}
            </CardTitle>
            <p className="text-muted-foreground">{user.email}</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
        {cardDetails.map(({ label, value }) => (
          <div key={label}>
            <p className="text-muted-foreground">{label}</p>
            <p className="break-words font-medium">{value}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ProfileCardLoading() {
  return (
    <Card>
      <CardHeader className="flex flex-col items-center justify-center gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          <Skeleton className="h-20 w-20 rounded-md" />
          <div className="space-y-2">
            <Skeleton className="h-7 w-40" />
            <Skeleton className="h-4 w-56" />
          </div>
        </div>
      </CardHeader>

      <CardContent className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="space-y-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function ProfilePage() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <Suspense fallback={<ProfileCardLoading />}>
        <ProfileCard />
      </Suspense>
    </section>
  );
}

function formatMaybeDate(value: Date | string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return formatDate(date, 'PPpp');
}
