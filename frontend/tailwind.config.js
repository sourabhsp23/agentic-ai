/** Tailwind is restricted to the design tokens: no default palette, 4px spacing scale only. */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      bg: { DEFAULT: token("bg"), subtle: token("bg-subtle"), muted: token("bg-muted") },
      border: { DEFAULT: token("border"), strong: token("border-strong") },
      fg: { DEFAULT: token("fg"), muted: token("fg-muted"), subtle: token("fg-subtle") },
      accent: {
        DEFAULT: token("accent"),
        hover: token("accent-hover"),
        fg: token("accent-fg"),
        subtle: token("accent-subtle"),
      },
      success: { DEFAULT: token("success"), subtle: token("success-subtle") },
      warning: { DEFAULT: token("warning"), subtle: token("warning-subtle") },
      danger: { DEFAULT: token("danger"), subtle: token("danger-subtle") },
      info: { DEFAULT: token("info"), subtle: token("info-subtle") },
    },
    spacing: {
      0: "0",
      px: "1px",
      1: "4px",
      2: "8px",
      3: "12px",
      4: "16px",
      6: "24px",
      8: "32px",
      12: "48px",
      16: "64px",
    },
    fontFamily: {
      sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
    },
    fontSize: {
      xs: ["12px", "16px"],
      sm: ["13px", "20px"],
      base: ["14px", "20px"],
      md: ["16px", "24px"],
      lg: ["20px", "28px"],
      xl: ["24px", "32px"],
    },
    fontWeight: { normal: "400", medium: "500", semibold: "600" },
    borderRadius: { none: "0", control: "5px", container: "8px", full: "9999px" },
    boxShadow: { none: "none", 1: "var(--shadow-1)", 2: "var(--shadow-2)" },
    transitionDuration: { DEFAULT: "var(--duration)" },
    transitionTimingFunction: { DEFAULT: "var(--ease)" },
    extend: {
      width: { sidebar: "248px", rail: "320px" },
      height: { control: "36px", "control-sm": "32px", header: "48px", chart: "280px" },
      minHeight: { textarea: "80px", "control-sm": "32px" },
      gridTemplateColumns: {
        shell: "248px minmax(0, 1fr) 320px",
        trace: "16px 128px minmax(0, 1fr) auto",
        "trace-sm": "16px minmax(0, 1fr) auto",
        "trace-live": "16px minmax(0, 1fr)",
      },
      maxWidth: { content: "1600px", prose: "72ch", cell: "320px" },
      maxHeight: { table: "440px", code: "320px" },
      minWidth: { trigger: "var(--radix-select-trigger-width)" },
    },
  },
  plugins: [],
};
