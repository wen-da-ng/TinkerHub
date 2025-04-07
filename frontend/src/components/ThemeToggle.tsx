"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
    console.log("Current theme:", theme); // Debug output
  }, [theme]);
  
  if (!mounted) return null;

  return (
    <button
      onClick={() => {
        const newTheme = theme === "dark" ? "light" : "dark";
        console.log("Switching to theme:", newTheme); // Debug output
        setTheme(newTheme);
      }}
      className="p-2 rounded-full bg-neutral-100 dark:bg-neutral-800 transition-colors hover:bg-neutral-200 dark:hover:bg-neutral-700"
      aria-label="Toggle theme"
    >
      {theme === "dark" ? (
        <Sun className="h-5 w-5 text-yellow-500" />
      ) : (
        <Moon className="h-5 w-5 text-indigo-700" />
      )}
    </button>
  );
}