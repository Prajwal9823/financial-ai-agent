import type { Config } from "tailwindcss";

// Design tokens kept centralized here so the whole app shares one
// consistent financial-dashboard palette instead of ad-hoc hex codes
// scattered across components.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#080b10", surface: "#10161e", border: "#27313e",
        accent: "#49e59c", danger: "#ff6f7d", muted: "#91a0b1",
      },
      boxShadow: { panel: "0 20px 60px rgba(0,0,0,.24)" },
    },
  },
  plugins: [],
};
export default config;
