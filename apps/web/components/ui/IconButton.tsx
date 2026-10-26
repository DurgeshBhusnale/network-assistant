import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "./cn";

export type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label"> & {
  /** Required: icon buttons have no visible text. */
  label: string;
  children: ReactNode;
};

export function IconButton({
  label,
  type = "button",
  className,
  children,
  ...rest
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      className={cn(
        "inline-flex size-tap shrink-0 items-center justify-center rounded-pill bg-surface text-ink hairline-strong",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
