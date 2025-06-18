import { Shirt } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export function Header() {
  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Shirt className="w-6 h-6 text-purple-600 mr-2" />
            <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              OutfitPredict
            </span>
          </div>
          <nav className="hidden md:flex space-x-6 items-center">
            <Link href="/wardrobe">
              <Button variant="outline" className="rounded-xl border border-purple-400 bg-white hover:bg-purple-50 text-purple-600 font-semibold shadow-sm transition-colors">
                View My Wardrobe
              </Button>
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}
