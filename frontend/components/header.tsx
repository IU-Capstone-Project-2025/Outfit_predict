import { Shirt } from "lucide-react"
import Link from "next/link"

export function Header() {
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
          <nav className="hidden md:flex space-x-6 items-center">
            {/* Removed View My Wardrobe button */}
          </nav>
        </div>
      </div>
    </header>
  )
}
