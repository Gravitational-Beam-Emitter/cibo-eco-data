"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  if (!mounted) return <div className="w-8 h-8" />;

  return (
    <button
      onClick={toggle}
      className="w-8 h-8 flex items-center justify-center rounded-xl glass text-muted hover:text-ink hover:brightness-105 transition-all cursor-pointer text-sm"
      aria-label={dark ? "切换亮色模式" : "切换暗色模式"}
    >
      {dark ? "☀" : "☾"}
    </button>
  );
}
