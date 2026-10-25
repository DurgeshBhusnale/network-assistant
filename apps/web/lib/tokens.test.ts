import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

/** Components and screens use design tokens only (CLAUDE.md): no raw hex colours. */
const ROOTS = ["components", "app"];
// Browser chrome and the manifest can't read CSS variables; both mirror tokens.css.
const ALLOWED = new Set([join("app", "layout.tsx"), join("app", "manifest.ts")]);
const HEX = /#[0-9a-fA-F]{3,8}\b/;

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === "__snapshots__" ? [] : files(path);
    return /\.(tsx?|css)$/.test(name) ? [path] : [];
  });
}

describe("design tokens", () => {
  it("has no raw hex colours outside the token mapping", () => {
    const offenders = ROOTS.flatMap(files)
      .filter((f) => !ALLOWED.has(f))
      .filter((f) => HEX.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });
});
