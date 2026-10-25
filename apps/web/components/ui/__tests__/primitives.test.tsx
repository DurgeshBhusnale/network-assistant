import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { Avatar, initials, tintIndex } from "../Avatar";
import { IconButton } from "../IconButton";
import { Input } from "../Input";
import { Stepper } from "../Stepper";

describe("Avatar", () => {
  it.each([
    ["Ananya Kulkarni", "AK"],
    ["Priya", "P"],
    ["  vikram  r  joshi ", "VJ"],
    ["", "?"],
  ])("initials(%j) = %s", (name, expected) => {
    expect(initials(name)).toBe(expected);
  });

  it("tints the same name the same way", () => {
    expect(tintIndex("Priya Nair")).toBe(tintIndex("Priya Nair"));
  });

  it("is decorative", () => {
    const { container } = render(<Avatar name="Priya Nair" />);
    expect(container.firstChild).toHaveAttribute("aria-hidden", "true");
  });
});

describe("IconButton", () => {
  it("has an accessible label and is 44 px", () => {
    render(
      <IconButton label="Snooze">
        <svg />
      </IconButton>,
    );
    expect(screen.getByRole("button", { name: "Snooze" })).toHaveClass("size-tap");
  });
});

describe("Input", () => {
  it("links its label, hint and error", () => {
    render(<Input label="Role you want" hint="e.g. Backend Engineer" error="Add a role" />);
    const input = screen.getByLabelText("Role you want");

    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("e.g. Backend Engineer Add a role");
  });
});

describe("Stepper", () => {
  function Harness() {
    const [value, setValue] = useState(4);
    return (
      <Stepper label="Referrals to aim for" value={value} min={1} max={5} onChange={setValue} />
    );
  }

  it("steps within bounds", async () => {
    render(<Harness />);
    const more = screen.getByRole("button", { name: "More" });

    await userEvent.click(more);
    expect(screen.getByRole("status")).toHaveTextContent("5");
    expect(more).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Fewer" }));
    expect(screen.getByRole("status")).toHaveTextContent("4");
    expect(screen.getByRole("group", { name: "Referrals to aim for" })).toBeInTheDocument();
  });
});
