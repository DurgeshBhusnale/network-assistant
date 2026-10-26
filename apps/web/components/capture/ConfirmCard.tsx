"use client";

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
  const meta = [
    candidate.title,
    candidate.company,
    candidate.where_met && `met at ${candidate.where_met}`,
  ]
    .filter(Boolean)
    .join(" · ");
  const status = forContact ? t.thisPerson : match ? t.possibleMatch : t.newContact;
  const skipped = choice.action === "discard";

  return (
    <Card className={cn(skipped && "opacity-60")}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-body font-semibold">{choice.fullName}</span>
        <span
          className={cn(
            "shrink-0 rounded-badge px-2 py-[3px] text-tiny font-semibold",
            match || forContact ? "bg-primary-soft text-primary" : "bg-success-soft text-success",
          )}
        >
          {status}
        </span>
      </div>
      {meta && <p className="text-small text-ink-2">{meta}</p>}
      {match && !forContact && choice.action !== "discard" && (
        <p className="text-small text-ink-2">{t.isThis(match.full_name)}</p>
      )}
      {candidate.facts.length > 0 && (
        <ul className="m-0 pl-5 text-small text-ink">
          {candidate.facts.map((f) => (
            <li key={f}>{f}</li>
          ))}
          {candidate.commitments.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}
      {candidate.follow_up_date && (
        <p className="text-small font-semibold text-accent-text">
          {t.followUp(dateFmt.format(new Date(`${candidate.follow_up_date}T00:00:00`)))}
        </p>
      )}

      {choice.editing && (
        <div className="flex flex-col gap-2">
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

      <div className="flex flex-wrap gap-2">
        {match && !forContact ? (
          <>
            <Button
              variant={choice.action === "merge" ? "primary" : "secondary"}
              aria-pressed={choice.action === "merge"}
              onClick={() => onChange({ ...choice, action: "merge", contactId: match.contact_id })}
            >
              {t.yesMerge}
            </Button>
            <Button
              variant={choice.action === "new" ? "primary" : "secondary"}
              aria-pressed={choice.action === "new"}
              onClick={() => onChange({ ...choice, action: "new" })}
            >
              {t.newPerson}
            </Button>
          </>
        ) : (
          <Button
            variant={choice.action !== "discard" ? "primary" : "secondary"}
            aria-pressed={choice.action !== "discard"}
            onClick={() => onChange({ ...choice, action: forContact ? "merge" : "new" })}
          >
            {t.save}
          </Button>
        )}
        {!forContact && (
          <Button variant="ghost" onClick={() => onChange({ ...choice, editing: !choice.editing })}>
            {choice.editing ? t.done : t.edit}
          </Button>
        )}
        <Button
          variant="ghost"
          aria-pressed={skipped}
          onClick={() => onChange({ ...choice, action: "discard" })}
        >
          {t.discardPerson}
        </Button>
      </div>
    </Card>
  );
}
