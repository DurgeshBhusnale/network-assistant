import { render } from "@testing-library/react";

import { AppShell } from "../AppShell";

vi.mock("next/navigation", () => ({ usePathname: () => "/today" }));

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
