import { render, screen, within } from "@testing-library/react";

import { BottomNav } from "../BottomNav";

const pathname = vi.hoisted(() => ({ current: "/today" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

describe("BottomNav", () => {
  beforeEach(() => {
    pathname.current = "/today";
  });

  it("shows five items with the capture button in the middle", () => {
    render(<BottomNav />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    const links = within(nav).getAllByRole("link");

    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "/today",
      "/people",
      "/capture",
      "/progress",
      "/replies",
    ]);
    expect(links[2]).toHaveAccessibleName("Capture by voice");
  });

  it("marks only the current tab as the current page", () => {
    pathname.current = "/people";
    render(<BottomNav />);

    const current = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("aria-current") === "page");
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent("People");
  });

  it("treats nested routes as the parent tab", () => {
    pathname.current = "/people/123";
    render(<BottomNav />);
    expect(screen.getByRole("link", { name: "People" })).toHaveAttribute("aria-current", "page");
  });

  it("shows the replies badge only when there are pending check-ins", () => {
    const { rerender } = render(<BottomNav repliesCount={0} />);
    expect(screen.queryByLabelText(/waiting for a reply check/)).not.toBeInTheDocument();

    rerender(<BottomNav repliesCount={3} />);
    expect(screen.getByLabelText("3 waiting for a reply check")).toHaveTextContent("3");
  });
});
