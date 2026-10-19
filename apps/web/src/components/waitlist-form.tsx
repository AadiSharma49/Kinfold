"use client";

import { useId, useState, type FormEvent } from "react";
import { roles } from "@/lib/waitlist";

type Status = "idle" | "submitting" | "success" | "duplicate" | "error";

export function WaitlistForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string>("");
  const [bringLength, setBringLength] = useState(0);

  const emailId = useId();
  const roleId = useId();
  const bringId = useId();
  const companyId = useId();
  const statusId = useId();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    const payload = {
      email: String(formData.get("email") ?? ""),
      role: String(formData.get("role") ?? ""),
      bring: String(formData.get("bring") ?? ""),
      company: String(formData.get("company") ?? ""),
    };

    setStatus("submitting");
    setMessage("");

    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (data.status === "ok") {
        setStatus("success");
        setMessage("You're on the list. We'll email you when there's news.");
        form.reset();
        setBringLength(0);
      } else if (data.status === "duplicate") {
        setStatus("duplicate");
        setMessage("You're already on the list.");
      } else {
        setStatus("error");
        setMessage(data.message || "Something went wrong. Try again.");
      }
    } catch {
      setStatus("error");
      setMessage("Something went wrong. Try again.");
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="flex flex-col gap-4"
      aria-describedby={statusId}
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor={emailId} className="text-sm font-medium">
          Email
        </label>
        <input
          id={emailId}
          name="email"
          type="email"
          required
          autoComplete="email"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          placeholder="you@example.com"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={roleId} className="text-sm font-medium">
          Role
        </label>
        <select
          id={roleId}
          name="role"
          required
          defaultValue=""
          className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          <option value="" disabled>
            Choose one
          </option>
          {roles.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={bringId} className="text-sm font-medium">
          What would you bring to Kinfold?{" "}
          <span className="text-muted-foreground">(optional)</span>
        </label>
        <textarea
          id={bringId}
          name="bring"
          maxLength={280}
          rows={3}
          onChange={(e) => setBringLength(e.target.value.length)}
          className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          aria-describedby={`${bringId}-count`}
        />
        <p
          id={`${bringId}-count`}
          className="text-right text-xs text-muted-foreground"
        >
          {bringLength}/280
        </p>
      </div>

      <div className="hidden" aria-hidden="true">
        <label htmlFor={companyId}>Company</label>
        <input
          id={companyId}
          name="company"
          type="text"
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      <button
        type="submit"
        disabled={status === "submitting"}
        className="rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {status === "submitting" ? "Joining..." : "Join the waitlist"}
      </button>

      <p
        id={statusId}
        role="status"
        aria-live="polite"
        className={`text-sm ${
          status === "error"
            ? "text-accent"
            : status === "success" || status === "duplicate"
              ? "text-foreground"
              : "sr-only"
        }`}
      >
        {message}
      </p>
    </form>
  );
}
