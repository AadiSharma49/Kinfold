import { NextResponse } from "next/server";
import { mkdir, readFile, appendFile } from "node:fs/promises";
import path from "node:path";
import { isRateLimited, waitlistSchema } from "@/lib/waitlist";

// Temporary storage until the FastAPI backend exists: one JSON line per signup.
const DATA_DIR = path.join(process.cwd(), "data");
const DATA_FILE = path.join(DATA_DIR, "waitlist.jsonl");

export async function POST(request: Request) {
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "unknown";

  if (isRateLimited(ip)) {
    return NextResponse.json(
      { status: "error", message: "Too many requests. Try again later." },
      { status: 429 }
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { status: "error", message: "Invalid request body." },
      { status: 400 }
    );
  }

  const parsed = waitlistSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { status: "error", message: "Please check the form and try again." },
      { status: 400 }
    );
  }

  const { email, role, bring, company } = parsed.data;

  // Honeypot: real users never fill this hidden field.
  if (company) {
    return NextResponse.json({ status: "ok" });
  }

  try {
    await mkdir(DATA_DIR, { recursive: true });

    let existing = "";
    try {
      existing = await readFile(DATA_FILE, "utf8");
    } catch {
      existing = "";
    }

    const alreadyExists = existing
      .split("\n")
      .filter(Boolean)
      .some((line) => {
        try {
          return JSON.parse(line).email === email;
        } catch {
          return false;
        }
      });

    if (alreadyExists) {
      return NextResponse.json(
        { status: "duplicate", message: "You're already on the list." },
        { status: 200 }
      );
    }

    const entry = {
      email,
      role,
      bring: bring || undefined,
      createdAt: new Date().toISOString(),
    };

    await appendFile(DATA_FILE, JSON.stringify(entry) + "\n", "utf8");

    return NextResponse.json({ status: "ok" });
  } catch {
    return NextResponse.json(
      { status: "error", message: "Something went wrong. Try again." },
      { status: 500 }
    );
  }
}
