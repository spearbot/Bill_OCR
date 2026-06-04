"use client";

import { useAuthStore } from "@/store/auth";
import { useTheme } from "next-themes";
import { Sun, Moon, User } from "lucide-react";

export function Header() {
  const user = useAuthStore((state) => state.user);
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 lg:px-6">
      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <div className="flex flex-1" />

        <div className="flex items-center gap-x-4">
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {theme === "dark" ? (
              <Sun className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            ) : (
              <Moon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            )}
          </button>

          <div className="flex items-center gap-x-3">
            <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
              <User className="h-4 w-4 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.name}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
