import { Shirt } from "lucide-react"
import Link from "next/link"
import { useAuth } from "@/lib/auth-context"
import { ChevronDown } from "lucide-react"
import { useState } from "react"

export function Header() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <header className="bg-white backdrop-blur-sm border-b border-gray-200/50 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center group focus-visible:outline-none focus:outline-none rounded-md transition"
          >
            <Shirt className="w-6 h-6 text-purple-600 mr-2 group-hover:scale-110 transition-transform" />
            <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent group-hover:underline">
              OutfitPredict
            </span>
          </Link>
          <nav className="flex items-center justify-end" style={{ minWidth: 220, height: 40 }}>
            {user ? (
              <div className="relative w-full flex justify-end">
                <button
                  className="flex items-center space-x-2 px-4 py-2 rounded-md hover:bg-gray-100 focus:outline-none"
                  onClick={() => setMenuOpen((v) => !v)}
                  style={{ minWidth: 160 }}
                >
                  <span className="font-medium text-gray-700 truncate max-w-[100px]">{user.email}</span>
                  <ChevronDown className={`w-4 h-4 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white border border-gray-200 rounded-xl shadow-lg z-10">
                    <button
                      className="w-full text-left px-4 py-2 text-red-600 hover:bg-red-50 rounded-xl"
                      onClick={() => { logout(); setMenuOpen(false); }}
                    >
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ minWidth: 160, height: 40 }} aria-hidden="true" />
            )}
          </nav>
        </div>
      </div>
    </header>
  )
}
