"use client";

import { useState, useSyncExternalStore, type ReactNode } from "react";
import { Card } from "@/components/ui/Card";

const STORAGE_KEY = "pb_admin_key";
// Same-tab writes don't fire the native `storage` event (only other tabs see
// that), so a manual event covers this tab; the native event still covers
// admin.html unlocking this page (or vice versa) from another tab for free.
const KEY_CHANGED_EVENT = "pb-admin-key-changed";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(KEY_CHANGED_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(KEY_CHANGED_EVENT, callback);
  };
}

function getSnapshot() {
  return window.localStorage.getItem(STORAGE_KEY);
}

function getServerSnapshot() {
  return null;
}

function writeAdminKey(value: string | null) {
  if (value == null) {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, value);
  }
  window.dispatchEvent(new Event(KEY_CHANGED_EVENT));
}

export function PassphraseGate({
  children,
}: {
  children: (adminKey: string, invalidate: (message?: string) => void) => ReactNode;
}) {
  const adminKey = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [error, setError] = useState<string | null>(null);
  const [value, setValue] = useState("");

  function invalidate(message?: string) {
    writeAdminKey(null);
    setError(message ?? null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    writeAdminKey(trimmed);
    setError(null);
  }

  if (!adminKey) {
    return (
      <form onSubmit={handleSubmit} className="mx-auto mt-20 max-w-sm">
        <Card>
          <label className="label" htmlFor="admin-key">
            Admin passphrase
          </label>
          <input
            id="admin-key"
            type="password"
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="tap mt-2 w-full rounded-lg border border-border bg-paper px-3 py-2 text-ui"
          />
          {error && <p className="mt-2 text-small text-danger">{error}</p>}
          <button
            type="submit"
            className="tap mt-4 w-full rounded-lg border border-accent bg-accent/10 px-3 py-2 font-mono text-caption uppercase tracking-wider text-accent transition-colors hover:bg-accent/20"
          >
            Unlock
          </button>
        </Card>
      </form>
    );
  }

  return <>{children(adminKey, invalidate)}</>;
}
