"use client";

import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { copy } from "@/lib/copy/en";

const t = copy.contactForm;

export type ContactFormValues = {
  full_name: string;
  phones: string[];
  emails: string[];
  linkedin_url: string;
  company: string;
  title: string;
  city: string;
  how_known: string;
  birthday: string;
};

export const emptyContact: ContactFormValues = {
  full_name: "",
  phones: [],
  emails: [],
  linkedin_url: "",
  company: "",
  title: "",
  city: "",
  how_known: "",
  birthday: "",
};

function lines(value: string): string[] {
  return value
    .split(/\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function Textarea({
  label,
  value,
  onChange,
  placeholder,
  rows = 2,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-small font-semibold">
        {label}
      </label>
      <textarea
        id={id}
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-button border border-line-strong bg-surface p-3 text-body"
      />
    </div>
  );
}

/** Add/edit person (FR-CON-4). `multi` shows all phones/emails (edit); new shows one of each. */
export function ContactForm({
  initial,
  multi,
  submitLabel,
  busy,
  error,
  onSubmit,
}: {
  initial: ContactFormValues;
  multi: boolean;
  submitLabel: string;
  busy: boolean;
  error: string | null;
  onSubmit: (values: ContactFormValues) => void;
}) {
  const [v, setV] = useState(initial);
  const [phones, setPhones] = useState(initial.phones.join("\n"));
  const [emails, setEmails] = useState(initial.emails.join("\n"));
  const set = (field: keyof ContactFormValues) => (value: string) =>
    setV((current) => ({ ...current, [field]: value }));

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({ ...v, phones: lines(phones), emails: lines(emails) });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <Input
        label={t.name}
        required
        autoComplete="off"
        value={v.full_name}
        onChange={(e) => set("full_name")(e.target.value)}
      />
      {multi ? (
        <>
          <Textarea label={t.phones} value={phones} onChange={setPhones} />
          <Textarea label={t.emails} value={emails} onChange={setEmails} />
        </>
      ) : (
        <>
          <Input
            label={t.phone}
            type="tel"
            inputMode="tel"
            value={phones}
            onChange={(e) => setPhones(e.target.value)}
          />
          <Input
            label={t.email}
            type="email"
            inputMode="email"
            value={emails}
            onChange={(e) => setEmails(e.target.value)}
          />
        </>
      )}
      <Input
        label={t.linkedin}
        inputMode="url"
        value={v.linkedin_url}
        onChange={(e) => set("linkedin_url")(e.target.value)}
      />
      <div className="grid grid-cols-2 gap-3">
        <Input
          label={t.company}
          value={v.company}
          onChange={(e) => set("company")(e.target.value)}
        />
        <Input label={t.title} value={v.title} onChange={(e) => set("title")(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Input label={t.city} value={v.city} onChange={(e) => set("city")(e.target.value)} />
        <Input
          label={t.birthday}
          type="date"
          value={v.birthday}
          onChange={(e) => set("birthday")(e.target.value)}
        />
      </div>
      <Textarea
        label={t.howKnown}
        placeholder={t.howKnownPlaceholder}
        value={v.how_known}
        onChange={set("how_known")}
      />
      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" fullWidth loading={busy} disabled={v.full_name.trim() === ""}>
        {submitLabel}
      </Button>
    </form>
  );
}

/** Empty strings become null so the API clears fields the user emptied. */
export function blankToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
