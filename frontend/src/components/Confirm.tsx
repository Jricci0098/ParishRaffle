import { ReactNode } from "react";

interface Props {
  open: boolean;
  title: string;
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Full-screen confirmation modal for destructive / important actions. */
export function Confirm({
  open,
  title,
  message,
  confirmLabel = "Yes",
  cancelLabel = "Cancel",
  danger,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="card w-full max-w-lg text-center">
        <h2 className="text-3xl font-black mb-4">{title}</h2>
        {message && <div className="text-xl text-slate-600 mb-6">{message}</div>}
        <div className="flex gap-4">
          <button className="btn-neutral flex-1" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            className={`flex-1 ${danger ? "btn-danger" : "btn-success"}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
