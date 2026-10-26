import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ConsentsForm } from "../ConsentsForm";

const mutateAsync = vi.fn();

vi.mock("@/lib/api/hooks/account", () => ({
  useUpdateConsents: () => ({ mutateAsync, isPending: false }),
}));

beforeEach(() => mutateAsync.mockReset().mockResolvedValue({}));

describe("ConsentsForm", () => {
  it("pre-ticks nothing: consent is an active opt-in (DPDP)", () => {
    render(<ConsentsForm initial={undefined} onSaved={vi.fn()} />);
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes).toHaveLength(5); // the notice + four itemised choices
    for (const box of boxes) expect(box).not.toBeChecked();
  });

  it("won't continue until the notice is accepted", async () => {
    const onSaved = vi.fn();
    render(<ConsentsForm initial={undefined} onSaved={onSaved} />);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Tick the privacy notice box");
    expect(mutateAsync).not.toHaveBeenCalled();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("saves exactly the choices made", async () => {
    const onSaved = vi.fn();
    render(<ConsentsForm initial={undefined} onSaved={onSaved} submitLabel="Save" />);
    await userEvent.click(screen.getByRole("checkbox", { name: /read the privacy notice/ }));
    await userEvent.click(screen.getByRole("checkbox", { name: /Process my voice notes/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(mutateAsync).toHaveBeenCalledWith({
      accept_notice: true,
      consents: { contacts: false, voice: true, whatsapp: false, analytics: false },
    });
    expect(onSaved).toHaveBeenCalledOnce();
  });

  it("shows saved choices when editing from Settings", () => {
    render(
      <ConsentsForm
        initial={{
          notice_version: "v1",
          notice_accepted: true,
          consents: {
            contacts: { granted: true, version: "v1", granted_at: "2026-10-25T00:00:00Z" },
            voice: { granted: false, version: null, granted_at: null },
            whatsapp: { granted: true, version: "v1", granted_at: "2026-10-25T00:00:00Z" },
            analytics: { granted: false, version: null, granted_at: null },
          },
        }}
        onSaved={vi.fn()}
      />,
    );
    expect(screen.getByRole("checkbox", { name: /Import my contacts/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Message me on WhatsApp/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Process my voice notes/ })).not.toBeChecked();
  });
});
