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
      router.replace("/wardrobe")
    } catch (err: any) {
      setError(err.message || "Signup failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      heading="Sign Up"
      headingColor="text-purple-700"
      buttonText={loading ? "Signing up..." : "Sign Up"}
      buttonGradient="bg-gradient-to-r from-purple-600 to-pink-600"
      buttonHoverGradient="hover:from-purple-700 hover:to-pink-700"
      inputFocusRing="focus:ring-purple-500"
      backgroundGradient="bg-gradient-to-br from-purple-50 via-white to-pink-50"
      bottomText="Already have an account?"
      bottomLink="Sign In"
      bottomLinkHref="/login"
      bottomLinkColor="text-purple-600"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-gray-700 font-semibold mb-2">Email</label>
          <input
            type="email"
            className={`w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 ${"focus:ring-purple-500"}`}
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div>
          <label className="block text-gray-700 font-semibold mb-2">Password</label>
          <input
            type="password"
            className={`w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 ${"focus:ring-purple-500"}`}
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <div className="text-red-600 text-sm text-center">{error}</div>}
        <button
          type="submit"
          className={`w-full ${"bg-gradient-to-r from-purple-600 to-pink-600"} text-white font-semibold py-3 rounded-xl shadow-lg ${"hover:from-purple-700 hover:to-pink-700"} transition-all duration-200`}
          disabled={loading}
        >
          {loading ? "Signing up..." : "Sign Up"}
        </button>
      </form>
    </AuthLayout>
  )
}
