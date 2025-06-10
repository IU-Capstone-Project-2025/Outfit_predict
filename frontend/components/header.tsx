import { Shirt } from "lucide-react"

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
          <nav className="hidden md:flex space-x-6">
            <a href="#" className="text-gray-600 hover:text-purple-600 transition-colors">
              How it Works
            </a>
            <a href="#" className="text-gray-600 hover:text-purple-600 transition-colors">
              About
            </a>
            <a href="#" className="text-gray-600 hover:text-purple-600 transition-colors">
              Contact
            </a>
          </nav>
        </div>
      </div>
    </header>
  )
}
