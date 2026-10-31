import { globalIgnores } from "eslint/config";
import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

const config = [
  globalIgnores([
    "node_modules/**",
    ".next/**",
    "out/**",
    "coverage/**",
    "next-env.d.ts",
  ]),
  ...coreWebVitals,
  ...typescript,
];

export default config;
