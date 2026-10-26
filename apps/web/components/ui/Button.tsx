import type { ButtonHTMLAttributes } from "react";

import { cn } from "./cn";

/**
 * v4: the gradient is reserved for the primary action; secondary actions use a hairline,
 * tonal ones the soft accent fill, and "dark" a solid ink fill (e.g. "Yes, merge").
 */
export type ButtonVariant = "primary" | "secondary" | "tonal" | "dark" | "ghost" | "danger";
export type ButtonSize = "md" | "lg";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-grad text-on-primary",
  secondary: "bg-surface text-ink hairline-strong hover:bg-surface-2",
  tonal: "bg-primary-soft text-primary hover:text-primary-hover",
  dark: "bg-ink text-on-primary",
  ghost: "bg-transparent text-primary hover:text-primary-hover",
  danger: "bg-surface text-danger hairline-strong hover:bg-danger-soft",
};

const sizes: Record<ButtonSize, string> = {
  md: "min-h-button rounded-button px-5 text-[15px]",
  lg: "min-h-cta rounded-button-lg px-7 text-[16px]",
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  disabled,
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      data-variant={variant}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-semibold transition-[color,background-color,opacity]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        sizes[size],
        variant === "primary" && size === "lg" && "shadow-cta",
        variant === "ghost" && "px-0",
        fullWidth && "w-full",
        className,
      )}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="size-4 animate-spin rounded-pill border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  );
}

/** Same look as Button for links (e.g. "Add your contacts" → /people/import). */
export function buttonClasses({
  variant = "primary",
  size = "md",
  fullWidth = false,
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}): string {
  return cn(
    "inline-flex items-center justify-center gap-2 font-semibold no-underline",
    variants[variant],
    sizes[size],
    variant === "primary" && "hover:text-on-primary",
    variant === "primary" && size === "lg" && "shadow-cta",
    fullWidth && "w-full",
  );
}
