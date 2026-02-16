import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
    />
  );
}

export function WorkflowCardSkeleton() {
  return (
    <div className="border rounded-lg p-4 flex items-center justify-between">
      <div className="flex-1 space-y-2">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-72" />
        <div className="flex items-center gap-4 mt-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-32" />
        </div>
      </div>
      <Skeleton className="h-8 w-8 rounded" />
    </div>
  );
}

export function WorkflowListSkeleton() {
  return (
    <div className="grid gap-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <WorkflowCardSkeleton key={i} />
      ))}
    </div>
  );
}
