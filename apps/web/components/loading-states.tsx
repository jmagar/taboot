import { Skeleton } from '@taboot/ui/components/skeleton';

/**
 * Loading skeleton for page headers with title and description.
 * Use for: Page titles, section headers
 */
export function PageHeaderLoading() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96" />
    </div>
  );
}

/**
 * Loading skeleton for card components.
 * Use for: Dashboard cards, info panels, content blocks
 */
export function CardLoading() {
  return (
    <div className="rounded-lg border p-6 space-y-4">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  );
}

/**
 * Loading skeleton for form inputs.
 * Use for: Login forms, settings forms, any input-heavy pages
 * @example
 * <Suspense fallback={<FormLoading />}>
 *   <MyForm />
 * </Suspense>
 */
export function FormLoading() {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-full" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-full" />
      </div>
      <Skeleton className="h-10 w-32" />
    </div>
  );
}

/**
 * Loading skeleton for settings pages.
 * Use for: Settings routes, configuration pages
 */
export function SettingsLoading() {
  return (
    <div className="max-w-2xl space-y-8 p-12">
      <PageHeaderLoading />
      <CardLoading />
      <CardLoading />
    </div>
  );
}

/**
 * Loading skeleton for sidebar navigation.
 * Use for: App sidebar, navigation menus
 */
export function SidebarLoading() {
  return (
    <div className="w-64 border-r p-4 space-y-4">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-8 w-full" />
      <Skeleton className="h-8 w-full" />
      <Skeleton className="h-8 w-full" />
    </div>
  );
}

/**
 * Generic loading skeleton for page content.
 * Use for: Simple pages with minimal content
 */
export function PageLoading() {
  return (
    <div className="p-12">
      <PageHeaderLoading />
    </div>
  );
}

/**
 * Loading skeleton for data tables.
 * Use for: Lists, tables, data grids
 * @param rows - Number of skeleton rows to display (default: 5)
 */
export function TableLoading({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 border-b pb-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-24 ml-auto" />
      </div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4 py-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-24 ml-auto" />
        </div>
      ))}
    </div>
  );
}

/**
 * Loading skeleton for vertical lists.
 * Use for: Item lists, menu lists, search results
 * @param items - Number of skeleton items to display (default: 4)
 */
export function ListLoading({ items = 4 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }, (_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-lg border p-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Loading skeleton for grid layouts.
 * Use for: Card grids, image galleries, product grids
 * @param columns - Number of columns in the grid (default: 3)
 * @param items - Number of skeleton items to display (default: 6)
 */
export function GridLoading({ columns = 3, items = 6 }: { columns?: number; items?: number }) {
  return (
    <div
      className="grid gap-4"
      style={{
        gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
      }}
    >
      {Array.from({ length: items }, (_, i) => (
        <div key={i} className="rounded-lg border p-4 space-y-3">
          <Skeleton className="h-40 w-full rounded" />
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ))}
    </div>
  );
}

/**
 * Loading skeleton for profile pages.
 * Use for: User profile pages, account information displays
 */
export function ProfileLoading() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <div className="rounded-lg border">
        <div className="flex flex-col items-center justify-center gap-4 p-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-4">
            <Skeleton className="h-20 w-20 rounded-md" />
            <div className="space-y-2">
              <Skeleton className="h-7 w-40" />
              <Skeleton className="h-4 w-56" />
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 p-6 text-sm sm:grid-cols-2">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-32" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Loading skeleton for auth forms with centered layout.
 * Use for: Sign in, sign up, password reset forms
 */
export function AuthFormLoading() {
  return (
    <div className="flex min-h-svh items-center justify-center p-6 md:p-10">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <Skeleton className="mx-auto h-9 w-48" />
          <Skeleton className="mx-auto h-5 w-64" />
        </div>
        <div className="rounded-xl border p-6 shadow-sm">
          <div className="space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-10 w-full" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-10 w-full" />
            </div>
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
        <Skeleton className="mx-auto h-4 w-56" />
      </div>
    </div>
  );
}
