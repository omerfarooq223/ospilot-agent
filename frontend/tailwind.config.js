/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#080b0a",
          900: "#0e1413",
          850: "#131a18",
          800: "#19201e",
          700: "#212a28",
          600: "#2b3634",
          500: "#3c4a47",
        },
        mint: {
          200: "#a7f3e0",
          300: "#6eead0",
          400: "#3fd6bb",
          500: "#22b89e",
          600: "#158f7a",
        },
        signal: {
          amber300: "#f6cf98",
          amber400: "#eab766",
          amber500: "#d99a41",
          coral300: "#ffbcb2",
          coral400: "#ff8f83",
          coral500: "#ef6a5c",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Roboto Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(63, 214, 187, 0.25), 0 0 32px rgba(63, 214, 187, 0.14)",
        ring: "0 0 0 1px rgba(63, 214, 187, 0.4)",
      },
      borderRadius: {
        panel: "6px",
      },
    },
  },
  plugins: [],
};