/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Hanken Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"Geist Mono"', '"Fira Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          900: "#0F1B2D",
          700: "#1F3147",
        },
        signal: {
          600: "#2563EB",
          100: "#DBEAFE",
          50:  "#EFF6FF",
        },
        permitido:   "#16A34A",
        denegado:    "#DC2626",
        advertencia: "#D97706",
      },
      boxShadow: {
        card:     "0 1px 3px rgba(15,27,45,.10)",
        panel:    "0 12px 40px rgba(15,27,45,.14)",
        veredicto:"0 16px 48px rgba(15,27,45,.30)",
      },
      borderRadius: {
        DEFAULT: "8px",
        card:    "12px",
        modal:   "16px",
      },
    },
  },
  plugins: [],
};
