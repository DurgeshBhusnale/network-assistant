"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Sheet } from "@/components/ui/Sheet";
import { ApiError } from "@/lib/api/client";
import { useActiveGoal, usePacks } from "@/lib/api/hooks/account";
import { useCreateDraft } from "@/lib/api/hooks/drafts";
import { copy } from "@/lib/copy/en";

type StageInfo = { id: string; label: string; step: number; has_ask: boolean };

/** Choose the message stage from the active goal's pack config, then generate a draft. */
export function StagePicker({
  contactId,
  open,
  onClose,
}: {
  contactId: string;
  open: boolean;
  onClose: () => void;
}) {
  const goal = useActiveGoal();
  const packs = usePacks();
  const create = useCreateDraft(contactId);
  const router = useRouter();
  const t = copy.draft;

  const pack = packs.data?.find((p) => p.id === goal.data?.pack_id);
  const descriptions = (pack?.copy_text.stage_descriptions ?? {}) as Record<string, string>;
  const stages = (pack?.stages ?? []) as StageInfo[];

  async function pick(stage: string) {
    try {
      const draft = await create.mutateAsync({ stage });
      router.push(`/drafts/${draft.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push(`/upgrade?reason=${e.code === "FREE_REGEN_LIMIT_REACHED" ? "regen" : "free"}`);
      }
    }
  }

  const error = create.error instanceof ApiError ? create.error : null;

  return (
    <Sheet open={open} title={t.chooseStage} onClose={onClose}>
      {goal.data === null ? (
        <div className="flex flex-col gap-2">
          <p className="text-body">{t.noGoal}</p>
          <Link href="/onboarding/goal" className="font-semibold">
            {t.setGoal}
          </Link>
        </div>
      ) : create.isPending ? (
        <p role="status" aria-live="polite" className="py-6 text-center text-body text-ink-2">
          {t.writing}
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {stages.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => void pick(s.id)}
                className="flex min-h-[56px] w-full flex-col items-start justify-center rounded-card border border-line bg-surface px-card text-left"
              >
                <span className="text-body font-semibold">{s.label}</span>
                {descriptions[s.id] && (
                  <span className="text-small text-muted">{descriptions[s.id]}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && error.status !== 402 && (
        <p role="alert" className="text-small text-danger">
          {error.message}
        </p>
      )}
    </Sheet>
  );
}
