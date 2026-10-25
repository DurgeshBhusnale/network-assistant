import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Use the generated API client and hooks in lib/api/." },
      ],
    },
  },
  {
    files: ["e2e/**", "lib/api/**", "**/*.test.ts", "**/*.test.tsx"],
    rules: { "no-restricted-globals": "off" },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "public/sw.js",
    "playwright-report/**",
    "test-results/**",
  ]),
]);

export default eslintConfig;
