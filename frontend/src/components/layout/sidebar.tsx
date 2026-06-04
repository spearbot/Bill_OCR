"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import {
  LayoutDashboard,
  Upload,
  FileText,
  Table2,
  Settings,
  Shield,
  Pill,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/dataset", icon: LayoutDashboard },
  { name: "Upload Bills", href: "/upload", icon: Upload },
  { name: "Bills", href: "/bills", icon: FileText },
  { name: "Dataset", href: "/dataset", icon: Table2 },
  { name: "Settings", href: "/settings", icon: Settings },
];

const adminNavigation = [
  { name: "Admin Panel", href: "/admin", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const isAdmin = user?.role === "admin";

  return (
    <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
      <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6">
        <div className="flex h-16 shrink-0 items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <Pill className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">Bill OCR</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Medical Platform</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col">
          <ul role="list" className="flex flex-1 flex-col gap-y-7">
            <li>
              <ul role="list" className="-mx-2 space-y-1">
                {navigation.map((item) => (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={cn(
                        pathname === item.href
                          ? "bg-gray-50 dark:bg-gray-700 text-primary-600 dark:text-primary-400"
                          : "text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-gray-50 dark:hover:bg-gray-700",
                        "group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-medium transition-colors"
                      )}
                    >
                      <item.icon className="h-5 w-5 shrink-0" />
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </li>

            {isAdmin && (
              <li>
                <ul role="list" className="-mx-2 space-y-1">
                  <li className="text-xs font-semibold leading-6 text-gray-400 dark:text-gray-500 uppercase tracking-wider px-2">
                    Admin
                  </li>
                  {adminNavigation.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className={cn(
                          pathname === item.href
                            ? "bg-gray-50 dark:bg-gray-700 text-primary-600 dark:text-primary-400"
                            : "text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-gray-50 dark:hover:bg-gray-700",
                          "group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-medium transition-colors"
                        )}
                      >
                        <item.icon className="h-5 w-5 shrink-0" />
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            )}

            <li className="-mx-6 mt-auto">
              <button
                onClick={logout}
                className="flex items-center gap-x-4 px-6 py-3 text-sm font-semibold leading-6 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 w-full transition-colors"
              >
                <LogOut className="h-5 w-5 shrink-0" />
                Sign out
              </button>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  );
}
