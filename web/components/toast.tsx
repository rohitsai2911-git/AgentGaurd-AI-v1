"use client";

import { CircleAlert, CircleCheck, Info, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/format";

export type ToastTone = "success" | "error" | "info";

interface ToastRecord {
  id: number;
  message: string;
  tone: ToastTone;
  title?: string;
}

interface ToastContextValue {
  push: (message: string, tone?: ToastTone, title?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return context;
}

const TONE_STYLES: Record<ToastTone, string> = {
  success: "bg-forest-ink text-linen-mist",
  error: "bg-paper text-obsidian",
  info: "bg-fog text-charcoal",
};

const TONE_ICON: Record<ToastTone, ReactNode> = {
  success: <CircleCheck size={18} strokeWidth={2} className="text-lime-voltage" />,
  error: <CircleAlert size={18} strokeWidth={2} className="text-obsidian" />,
  info: <Info size={18} strokeWidth={2} className="text-forest-ink" />,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (message: string, tone: ToastTone = "info", title?: string) => {
      const id = (nextId.current += 1);
      setToasts((current) => [...current.slice(-2), { id, message, tone, title }]);
      window.setTimeout(() => dismiss(id), 6500);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-60 flex flex-col items-stretch gap-2 p-4 sm:items-end sm:p-6"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "ag-rise pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-card px-4 py-3 sm:w-auto",
              TONE_STYLES[toast.tone],
              toast.tone === "error" ? "shadow-hairline-strong" : "",
            )}
          >
            <span className="mt-0.5 shrink-0">{TONE_ICON[toast.tone]}</span>
            <div className="min-w-0 flex-1">
              {toast.title ? (
                <p className="text-caption font-semibold">{toast.title}</p>
              ) : null}
              <p className="text-caption break-words">{toast.message}</p>
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss notification"
              className="-mr-1 shrink-0 rounded-full p-1 opacity-60 transition-opacity duration-150 ease-out hover:opacity-100"
            >
              <X size={15} strokeWidth={2} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}