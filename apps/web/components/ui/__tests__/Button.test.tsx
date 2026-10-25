import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Button } from "../Button";

describe("Button", () => {
  it("renders its label and handles clicks", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Open draft</Button>);

    await userEvent.click(screen.getByRole("button", { name: "Open draft" }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Send
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Send" });
    await userEvent.click(button);

    expect(button).toBeDisabled();
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is busy and disabled while loading", () => {
    render(<Button loading>Writing</Button>);
    const button = screen.getByRole("button", { name: "Writing" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it.each([
    ["md", "min-h-tap"],
    ["lg", "min-h-cta"],
  ] as const)("size %s meets the 44 px touch minimum via %s", (size, cls) => {
    render(<Button size={size}>Go</Button>);
    expect(screen.getByRole("button", { name: "Go" })).toHaveClass(cls);
  });

  it.each(["primary", "secondary", "accent", "send", "ghost"] as const)(
    "variant %s uses token classes",
    (variant) => {
      render(<Button variant={variant}>Go</Button>);
      const button = screen.getByRole("button", { name: "Go" });
      expect(button).toHaveAttribute("data-variant", variant);
      expect(button.className).not.toMatch(/#[0-9a-f]{3,6}/i);
    },
  );

  it("defaults to type=button so it never submits forms by accident", () => {
    render(<Button>Go</Button>);
    expect(screen.getByRole("button", { name: "Go" })).toHaveAttribute("type", "button");
  });
});
