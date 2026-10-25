import { contactPickerSupported, pickContacts } from "./contactPicker";
import { pushSupported } from "./push";

type Select = (...args: unknown[]) => Promise<unknown>;

function installPicker(select: Select) {
  Object.defineProperty(navigator, "contacts", { value: { select }, configurable: true });
  Object.defineProperty(window, "ContactsManager", { value: class {}, configurable: true });
}

afterEach(() => {
  Reflect.deleteProperty(navigator, "contacts");
  Reflect.deleteProperty(window, "ContactsManager");
});

describe("contact picker", () => {
  it("is unsupported without the API, and picking falls back to nothing", async () => {
    expect(contactPickerSupported()).toBe(false);
    await expect(pickContacts()).resolves.toEqual([]);
  });

  it("asks for name, phone and email, and fills missing fields", async () => {
    const select = vi.fn().mockResolvedValue([{ name: ["Priya"], tel: ["+91 98765 43210"] }]);
    installPicker(select);
    expect(contactPickerSupported()).toBe(true);
    await expect(pickContacts()).resolves.toEqual([
      { name: ["Priya"], tel: ["+91 98765 43210"], email: [] },
    ]);
    expect(select).toHaveBeenCalledWith(["name", "tel", "email"], { multiple: true });
  });

  it("treats a cancelled picker as an empty pick", async () => {
    installPicker(vi.fn().mockRejectedValue(new DOMException("cancelled", "AbortError")));
    await expect(pickContacts()).resolves.toEqual([]);
  });
});

describe("push", () => {
  it("is unsupported where the browser has no PushManager", () => {
    expect(pushSupported()).toBe(false);
  });
});
