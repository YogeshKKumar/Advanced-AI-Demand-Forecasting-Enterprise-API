export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        ocean: "#155e75",
        mint: "#14b8a6",
        amber: "#f59e0b",
        cloud: "#f4f7fb"
      },
      boxShadow: {
        panel: "0 22px 70px rgba(15, 23, 42, 0.12)"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Arial"]
      }
    }
  },
  plugins: []
};
