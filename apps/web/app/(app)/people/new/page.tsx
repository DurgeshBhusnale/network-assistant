"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/shell/PageHeader";
import {
  blankToNull,
  ContactForm,
  emptyContact,
  type ContactFormValues,
} from "@/components/people/ContactForm";
import { ApiError } from "@/lib/api/client";
import { useCreateContact } from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";

export default function NewPersonPage() {
  const create = useCreateContact();
  const router = useRouter();

  async function submit(v: ContactFormValues) {
    try {
      const contact = await create.mutateAsync({
        full_name: v.full_name.trim(),
        phone: v.phones[0] ?? null,
        email: v.emails[0] ?? null,
        linkedin_url: blankToNull(v.linkedin_url),
        company: blankToNull(v.company),
        title: blankToNull(v.title),
        city: blankToNull(v.city),
        how_known: blankToNull(v.how_known),
        birthday: blankToNull(v.birthday),
      });
      router.replace(`/people/${contact.id}`);
    } catch {
      // The error is shown from the mutation state below.
    }
  }

  const error = create.error
    ? create.error instanceof ApiError
      ? create.error.message
      : copy.common.genericError
    : null;

  return (
    <>
      <PageHeader title={copy.contactForm.newTitle} />
      <div className="px-screen-x pt-2">
        <ContactForm
          initial={emptyContact}
          multi={false}
          submitLabel={copy.contactForm.create}
          busy={create.isPending}
          error={error}
          onSubmit={submit}
        />
      </div>
    </>
  );
}
