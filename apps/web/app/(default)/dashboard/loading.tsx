import { Skeleton } from '@taboot/ui/components/skeleton';

export default function DashboardLoading() {
  return (
    <section className="max-w-2xl p-12">
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="rounded-md py-4">
          <Skeleton className="h-5 w-64" />
        </div>
      </div>
    </section>
  );
}
