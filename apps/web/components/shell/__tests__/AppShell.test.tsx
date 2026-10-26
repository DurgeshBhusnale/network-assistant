import { render } from "@testing-library/react";

import { AppShell, showsBottomNav, showsSidebar } from "../AppShell";

vi.mock("next/navigation", () => ({ usePathname: () => "/today" }));
vi.mock("@/lib/api/hooks/loop", () => ({ useRepliesPending: () => ({ data: undefined }) }));
vi.mock("@/lib/api/hooks/account", () => ({
  useMe: () => ({ data: undefined }),
  useActiveGoal: () => ({ data: undefined }),
  usePacks: () => ({ data: undefined }),
}));

describe("AppShell", () => {
  it("matches the snapshot", () => {
    const { container } = render(
      <AppShell>
        <p>Content</p>
      </AppShell>,
    );
    expect(container).toMatchSnapshot();
  });

  it.each([
    ["/today", true],
    ["/people", true],
    ["/progress", true],
    ["/replies", true],
    ["/people/abc", false],
    ["/drafts/abc", false],
    ["/capture", false],
    ["/settings", false],
    ["/settings/privacy", false],
  ])("bottom nav on %s: %s (detail screens use their own back control)", (path, shown) => {
    expect(showsBottomNav(path)).toBe(shown);
  });

  it.each([
    ["/today", true],
    ["/drafts/abc", true],
    ["/settings/privacy", true],
    ["/capture", false],
  ])("desktop sidebar on %s: %s (voice capture is full-bleed)", (path, shown) => {
    expect(showsSidebar(path)).toBe(shown);
  });
});
