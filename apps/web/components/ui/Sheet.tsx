"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Bottom sheet built on <dialog> (focus trap, Esc to close, backdrop). */
export function Sheet({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-label={title}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      className="m-0 mt-auto w-full max-w-none bg-transparent p-0 backdrop:bg-ink/40 sm:mx-auto sm:max-w-[480px]"
    >
      <div className="mx-auto flex w-full max-w-[480px] flex-col gap-3 rounded-t-panel bg-surface px-screen-x pt-4 pb-[calc(env(safe-area-inset-bottom)+20px)]">
        <div className="mx-auto h-1 w-10 rounded-pill bg-line" aria-hidden="true" />
        <h2 className="m-0 font-display text-h2 font-semibold">{title}</h2>
        {children}
      </div>
    </dialog>
  );
}
