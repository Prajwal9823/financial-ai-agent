import type { Config } from "tailwindcss";

// Design tokens kept centralized here so the whole app shares one
// consistent financial-dashboard palette instead of ad-hoc hex codes
// scattered across components.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0b0f14",
        surface: "#121821",
        border: "#1f2733",
        accent: "#3dd68c",   // gains / positive
        danger: "#f2545b",   // losses / negative
        muted: "#8592a3",
      },
    },
  },
  plugins: [],
};
export default config;
