"use client";

import { useParams, useRouter } from "next/navigation";

import { PageHeader } from "@/components/shell/PageHeader";
import { blankToNull, ContactForm, type ContactFormValues } from "@/components/people/ContactForm";
import { ApiError } from "@/lib/api/client";
import { usePerson, useUpdateContact, type Person } from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";

function toForm(p: Person): ContactFormValues {
  return {
    full_name: p.full_name,
    phones: p.phones,
    emails: p.emails,
    linkedin_url: p.linkedin_url ?? "",
    company: p.company ?? "",
    title: p.title ?? "",
    city: p.city ?? "",
    how_known: p.how_known ?? "",
    birthday: p.birthday ?? "",
  };
}

function EditForm({ person }: { person: Person }) {
  const update = useUpdateContact(person.id);
  const router = useRouter();

  async function submit(v: ContactFormValues) {
    try {
      await update.mutateAsync({
        full_name: v.full_name.trim(),
        phones: v.phones,
        emails: v.emails,
        linkedin_url: blankToNull(v.linkedin_url),
        company: blankToNull(v.company),
        title: blankToNull(v.title),
        city: blankToNull(v.city),
        how_known: blankToNull(v.how_known),
        birthday: blankToNull(v.birthday),
      });
      router.replace(`/people/${person.id}`);
    } catch {
      // Shown from the mutation state below.
    }
  }

  const error = update.error
    ? update.error instanceof ApiError
      ? update.error.message
      : copy.common.genericError
    : null;

  return (
    <ContactForm
      initial={toForm(person)}
      multi
      submitLabel={copy.contactForm.save}
      busy={update.isPending}
      error={error}
      onSubmit={submit}
    />
  );
}

export default function EditPersonPage() {
  const { id } = useParams<{ id: string }>();
  const person = usePerson(id);
  return (
    <>
      <PageHeader title={copy.contactForm.editTitle} />
      <div className="px-screen-x pt-2">
        {person.data ? (
          <EditForm person={person.data} />
        ) : (
          <p role="status" className="text-small text-muted">
            {person.isPending ? `${copy.common.loading}…` : copy.person.notFound}
          </p>
        )}
      </div>
    </>
  );
}
