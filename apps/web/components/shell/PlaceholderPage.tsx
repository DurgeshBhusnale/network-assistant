import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/EmptyState";

import { PageHeader } from "./PageHeader";

/** Sprint 0 placeholder for a tab; each feature sprint replaces it with the real screen. */
export function PlaceholderPage({
  title,
  body,
  children,
}: {
  title: string;
  body: string;
  children?: ReactNode;
}) {
  return (
    <>
      <PageHeader title={title} />
      <div className="flex flex-col gap-gap-cards px-screen-x pt-2">
        <EmptyState title={title} body={body} />
        {children}
      </div>
    </>
  );
}
