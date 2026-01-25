import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export const ProjectCardSkeleton = () => {
  return (
    <Card className="glass-panel">
      <CardHeader>
        <Skeleton className="h-6 w-3/4 bg-surface-2" />
        <Skeleton className="h-4 w-1/2 mt-2 bg-surface-2" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-32 w-full bg-surface-2" />
        <div className="flex gap-2 mt-4">
          <Skeleton className="h-9 w-20 bg-surface-2" />
          <Skeleton className="h-9 w-20 bg-surface-2" />
        </div>
      </CardContent>
    </Card>
  );
};

export const ProjectListSkeleton = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <ProjectCardSkeleton key={i} />
      ))}
    </div>
  );
};
