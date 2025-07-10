"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import Link from "next/link"
import AuthLayout from "@/components/AuthLayout"

export default function SignupPage() {
  const { signup } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    try {
      await signup(email, password)
      router.replace("/about")
    } catch (err: any) {
      setError(err.message || "Signup failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none">
        <svg className="w-full h-full" viewBox="0 0 1200 800" fill="none">
          <defs>
            <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
              <path d="M 80 0 L 0 0 0 80" fill="none" stroke="white" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>
      <div className="relative z-10 w-full max-w-md mx-auto bg-gray-900/80 border border-gray-700/50 rounded-3xl shadow-2xl p-10 backdrop-blur-md">
        <h1 className="text-3xl font-bold mb-8 text-center">Sign Up</h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-gray-300 font-semibold mb-2">Email</label>
            <input
              type="email"
              className="w-full px-4 py-3 border border-gray-700 bg-black/40 text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-white placeholder-gray-500"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-gray-300 font-semibold mb-2">Password</label>
            <input
              type="password"
              className="w-full px-4 py-3 border border-gray-700 bg-black/40 text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-white placeholder-gray-500"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>
          {error && <div className="text-red-400 text-sm text-center">{error}</div>}
          <button
            type="submit"
            className="w-full bg-white text-black font-semibold py-3 rounded-xl shadow-lg hover:bg-gray-100 transition-all duration-200"
            disabled={loading}
          >
            {loading ? "Signing up..." : "Sign Up"}
          </button>
        </form>
        <div className="mt-8 text-center text-gray-400">
          Already have an account?{' '}
          <Link href="/login" className="text-white underline hover:text-gray-300">Sign In</Link>
        </div>
      </div>
    </div>
  )
}
