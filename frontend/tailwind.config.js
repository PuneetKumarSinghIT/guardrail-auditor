/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Severity / risk palette — matches RiskScoreMeter thresholds
        risk: {
          low: "#16a34a", // green-600
          medium: "#d97706", // amber-600
          high: "#dc2626", // red-600
          critical: "#7f1d1d", // red-900 (dark red)
        },
        brand: {
          DEFAULT: "#0f172a", // slate-900
          accent: "#2563eb", // blue-600
        },
      },
    },
  },
  plugins: [],
};
