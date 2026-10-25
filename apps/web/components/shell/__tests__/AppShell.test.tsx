import { render } from "@testing-library/react";

import { AppShell } from "../AppShell";

vi.mock("next/navigation", () => ({ usePathname: () => "/today" }));
vi.mock("@/lib/api/hooks/loop", () => ({ useRepliesPending: () => ({ data: undefined }) }));

describe("AppShell", () => {
  it("matches the snapshot", () => {
    const { container } = render(
      <AppShell>
        <p>Content</p>
      </AppShell>,
    );
    expect(container).toMatchSnapshot();
  });
});
