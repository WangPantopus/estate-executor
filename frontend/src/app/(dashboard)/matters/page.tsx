import { Suspense } from "react";
import { LoadingState } from "@/components/layout/LoadingState";
import { MattersPageContent } from "./_components/MattersPageContent";

export default function MattersPage() {
  return (
    <Suspense fallback={<LoadingState variant="table" count={5} />}>
      <MattersPageContent />
    </Suspense>
  );
}
