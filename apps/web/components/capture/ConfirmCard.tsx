"use client";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { cn } from "@/components/ui/cn";
import { Input } from "@/components/ui/Input";
import type { CaptureCandidate } from "@/lib/api/hooks/captures";
import { copy } from "@/lib/copy/en";

const t = copy.capture;
const dateFmt = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "short",
});

export type CardChoice = {
  action: "new" | "merge" | "discard";
  contactId?: string;
  fullName: string;
  company: string;
  editing: boolean;
};

export function initialChoice(c: CaptureCandidate, forContact: boolean): CardChoice {
  const match = c.matches[0];
  return {
    action: forContact || match ? "merge" : "new",
    contactId: match?.contact_id,
    fullName: c.full_name,
    company: c.company ?? "",
    editing: false,
  };
}

/** One extracted person (FR-MEM-3): Save new / Merge with suggested / Edit / Skip. */
export function ConfirmCard({
  candidate,
  choice,
  forContact,
  onChange,
}: {
  candidate: CaptureCandidate;
  choice: CardChoice;
  forContact: boolean;
  onChange: (choice: CardChoice) => void;
}) {
  const match = candidate.matches[0];
  const role = [candidate.title, candidate.company].filter(Boolean).join(" at ");
  const isMatch = Boolean(match) && !forContact;
  const status = forContact ? t.thisPerson : isMatch ? t.possibleMatch : t.newContact;
  const skipped = choice.action === "discard";
  const title =
    isMatch && choice.action !== "discard" ? t.isThis(match!.full_name) : choice.fullName;
  const sub = [isMatch ? null : role, status, candidate.where_met && t.metAt(candidate.where_met)]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card className={cn(skipped && "opacity-60")}>
      <div className="flex items-center gap-3.5">
        <Avatar name={choice.fullName} />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-lead leading-[22px] font-semibold">{title}</span>
          <span className="text-small leading-5 text-muted">{sub}</span>
        </span>
      </div>
      {(candidate.facts.length > 0 || candidate.commitments.length > 0) && (
        <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
          {[...candidate.facts, ...candidate.commitments].map((f) => (
            <li key={f} className="flex gap-2.5 text-small leading-5 text-ink-2">
              <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-pill bg-grad" />
              {f}
            </li>
          ))}
        </ul>
      )}
      {candidate.follow_up_date && (
        <p className="m-0 rounded-[12px] bg-surface-2 px-3 py-2.5 text-small leading-5 text-ink-2">
          {t.followUp(dateFmt.format(new Date(`${candidate.follow_up_date}T00:00:00`)))}
        </p>
      )}

      {choice.editing && (
        <div className="flex flex-col gap-3">
          <Input
            label={t.nameLabel}
            value={choice.fullName}
            onChange={(e) => onChange({ ...choice, fullName: e.target.value })}
          />
          <Input
            label={t.companyLabel}
            value={choice.company}
            onChange={(e) => onChange({ ...choice, company: e.target.value })}
          />
        </div>
      )}

      <div className="flex gap-2.5">
        {isMatch ? (
          <>
            <Button
              variant={choice.action === "merge" ? "dark" : "secondary"}
              className="flex-1"
              aria-pressed={choice.action === "merge"}
              onClick={() => onChange({ ...choice, action: "merge", contactId: match!.contact_id })}
            >
              {t.yesMerge}
            </Button>
            <Button
              variant={choice.action === "new" ? "dark" : "secondary"}
              className="flex-1"
              aria-pressed={choice.action === "new"}
              onClick={() => onChange({ ...choice, action: "new" })}
            >
              {t.newPerson}
            </Button>
          </>
        ) : (
          <>
            <Button
              variant={choice.action !== "discard" ? "primary" : "secondary"}
              className="flex-1"
              aria-pressed={choice.action !== "discard"}
              onClick={() => onChange({ ...choice, action: forContact ? "merge" : "new" })}
            >
              {t.save}
            </Button>
            {!forContact && (
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => onChange({ ...choice, editing: !choice.editing })}
              >
                {choice.editing ? t.done : t.edit}
              </Button>
            )}
          </>
        )}
      </div>
      <Button
        variant="ghost"
        className="-mt-2 min-h-tap self-center text-small text-muted"
        aria-pressed={skipped}
        onClick={() => onChange({ ...choice, action: "discard" })}
      >
        {t.discardPerson}
      </Button>
    </Card>
  );
}
