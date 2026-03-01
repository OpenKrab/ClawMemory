import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(210 100% 98%)",
        foreground: "hsl(222 47% 11%)",
        primary: "hsl(186 83% 35%)"
      }
    }
  },
  plugins: []
};

export default config;
