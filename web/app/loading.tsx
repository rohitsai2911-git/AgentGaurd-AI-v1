import { BarChart3, Layers } from "lucide-react";
import { Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <div className="mx-auto w-full max-w-[1560px] px-4 py-8 sm:px-6">
      <div className="flex items-center gap-2 text-pebble">
        <Layers size={16} />
        <BarChart3 size={16} />
      </div>
      <Skeleton className="mt-3 h-4 w-24" />
      <Skeleton className="mt-3 h-10 w-80" />
      <Skeleton className="mt-3 h-4 w-full max-w-2xl" />

      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28" />
        ))}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <Skeleton className="h-72 lg:col-span-2" />
        <Skeleton className="h-72" />
      </div>
    </div>
  );
}