/** Contact Picker API (Android Chrome 80+). Feature-detected; callers fall back to vCard upload. */

export type PickedContact = { name: string[]; tel: string[]; email: string[] };

type ContactsManager = {
  select(
    properties: Array<"name" | "tel" | "email">,
    options: { multiple: boolean },
  ): Promise<Array<Partial<PickedContact>>>;
};

function manager(): ContactsManager | null {
  if (typeof navigator === "undefined" || typeof window === "undefined") return null;
  if (!("contacts" in navigator) || !("ContactsManager" in window)) return null;
  return (navigator as Navigator & { contacts: ContactsManager }).contacts;
}

export function contactPickerSupported(): boolean {
  return manager() !== null;
}

/** Opens the system picker. Resolves [] if the user cancels. */
export async function pickContacts(): Promise<PickedContact[]> {
  const contacts = manager();
  if (!contacts) return [];
  try {
    const picked = await contacts.select(["name", "tel", "email"], { multiple: true });
    return picked.map((c) => ({ name: c.name ?? [], tel: c.tel ?? [], email: c.email ?? [] }));
  } catch {
    return [];
  }
}
