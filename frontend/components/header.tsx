"use client"

import { Shirt, ChevronDown } from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import { usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Menu } from "lucide-react"

export function Header() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const pathname = usePathname()

  const isActive = (path: string) => pathname === path

  return (
    <header className="bg-black backdrop-blur-md border-b border-gray-700/50 sticky top-0 z-50 w-full">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between w-full px-6 py-5">
        <div className="flex flex-row items-center justify-between w-full md:w-auto">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center rounded-lg transition-all duration-200 outline-none focus:outline-none"
          >
            <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center mr-3 transition-transform duration-200 outline-none focus:outline-none">
              <Shirt className="w-5 h-5 text-black" />
            </div>
            <span className="text-2xl font-semibold text-white transition-colors tracking-tight">
              OutfitPredict
            </span>
          </Link>
          {/* User Info (on small screens, right-aligned) */}
          <div className="flex items-center space-x-4 md:hidden">
            {user ? (
              <div className="relative">
                <button
                  className="flex items-center space-x-3 px-4 py-2 rounded-full hover:bg-gray-800/50 focus:outline-none transition-all duration-200"
                  onClick={() => setMenuOpen((v) => !v)}
                >
                  <span className="font-semibold text-white truncate max-w-[120px]">
                    {user.email?.split("@")[0] || "User"}
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 text-gray-300 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`}
                  />
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-gray-900/95 backdrop-blur-sm border border-gray-700/50 rounded-2xl shadow-xl z-10">
                    <button
                      className="w-full text-left px-6 py-4 text-red-400 hover:bg-red-500/10 rounded-2xl transition-colors font-medium"
                      onClick={() => {
                        logout()
                        setMenuOpen(false)
                      }}
                    >
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link href="/login" className="text-gray-300 hover:text-white transition-colors font-medium">
                  Login
                </Link>
                <Link href="/signup">
                  <button className="bg-white text-black hover:bg-gray-100 rounded-full px-6 py-2 text-sm font-semibold transition-all duration-200 shadow-lg hover:shadow-xl">
                    Sign up
                  </button>
                </Link>
              </div>
            )}
          </div>
        </div>
        {/* Navigation Bar: below on small, inline on md+ */}
        <nav className="flex w-full justify-center mt-4 md:mt-0 md:w-auto md:justify-start space-x-2">
          <Link
            href="/"
            className={`px-6 py-3 rounded-full text-sm font-semibold transition-all duration-200 ${
              isActive("/") ? "bg-white text-black shadow-lg" : "text-gray-300 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            Generate
          </Link>
          <Link
            href="/about"
            className={`px-6 py-3 rounded-full text-sm font-semibold transition-all duration-200 ${
              isActive("/about")
                ? "bg-white text-black shadow-lg"
                : "text-gray-300 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            About
          </Link>
          <Link
            href="/profile"
            className={`px-6 py-3 rounded-full text-sm font-semibold transition-all duration-200 ${
              isActive("/profile")
                ? "bg-white text-black shadow-lg"
                : "text-gray-300 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            Profile
          </Link>
        </nav>
        {/* User Info (on md+, right-aligned) */}
        <div className="hidden md:flex items-center space-x-4">
          {user ? (
            <div className="relative">
              <button
                className="flex items-center space-x-3 px-4 py-2 rounded-full hover:bg-gray-800/50 focus:outline-none transition-all duration-200"
                onClick={() => setMenuOpen((v) => !v)}
              >
                <span className="font-semibold text-white truncate max-w-[120px]">
                  {user.email?.split("@")[0] || "User"}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-gray-300 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`}
                />
              </button>
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-gray-900/95 backdrop-blur-sm border border-gray-700/50 rounded-2xl shadow-xl z-10">
                  <button
                    className="w-full text-left px-6 py-4 text-red-400 hover:bg-red-500/10 rounded-2xl transition-colors font-medium"
                    onClick={() => {
                      logout()
                      setMenuOpen(false)
                    }}
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <Link href="/login" className="text-gray-300 hover:text-white transition-colors font-medium">
                Login
              </Link>
              <Link href="/signup">
                <button className="bg-white text-black hover:bg-gray-100 rounded-full px-6 py-2 text-sm font-semibold transition-all duration-200 shadow-lg hover:shadow-xl">
                  Sign up
                </button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
