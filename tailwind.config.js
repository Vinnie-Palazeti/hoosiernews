/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "**/*.py",
    "**/*.html", 
    "**/*.js",     
  ],
  theme: {
    extend: {
      fontSize: {
        "5xl": ["3rem", { lineHeight: "3rem" }],
        "6xl": ["3.75rem", { lineHeight: "3.75rem" }],
        "7xl": ["4.5rem", { lineHeight: "4.5rem" }],
        "8xl": ["6rem", { lineHeight: "6rem" }],
        "9xl": ["8rem", { lineHeight: "8rem" }],
      },
      borderColor: {
        'darker-neutral': 'hsl(var(--n) / 0.9)', // Higher contrast neutral
      },      
    },
  },

  plugins: [require("daisyui")],

  daisyui: {
    themes: ["light", "dark"],
  }
}
