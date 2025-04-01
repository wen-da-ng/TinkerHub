// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    // Ensure these paths correctly point to where your components and pages live
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',        // If you have a pages dir
    './src/components/**/*.{js,ts,jsx,tsx,mdx}', // Your components folder
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',          // Your app router folder
  ],
  darkMode: 'class', // This should already be correct from the previous step
  theme: {
    extend: {
      // Your theme extensions (optional)
    },
  },
  plugins: [],
}
export default config