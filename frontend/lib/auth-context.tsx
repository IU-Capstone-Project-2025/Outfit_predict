"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { useRouter } from "next/navigation"
import { getApiBaseUrl, apiUrl, fetchWithAuth } from "./utils"

interface User {
  email: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  signup: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter();

  // Helper to handle logout and redirect
  const handle401Logout = () => {
    setUser(null);
    router.replace('/login');
  };

  useEffect(() => {
    // On mount, check for token
    const token = localStorage.getItem("token")
    const email = localStorage.getItem("user_email")
    async function validateSession() {
      if (token) {
        try {
          const res = await fetchWithAuth(apiUrl('v1/auth/me'), {}, handle401Logout)
          if (!res.ok) throw new Error('Invalid session')
          const data = await res.json()
          // Optionally update email from backend
          setUser({ email: data.email })
        } catch {
          localStorage.removeItem("token")
          localStorage.removeItem("user_email")
          setUser(null)
        }
      } else {
        setUser(null)
      }
      setLoading(false)
    }
    validateSession()
  }, [])

  function setTokenCookie(token: string) {
    // Set cookie for 7 days, path=/
    document.cookie = `token=${token}; path=/; max-age=${60 * 60 * 24 * 7}`
  }

  const login = async (email: string, password: string) => {
    const form = new URLSearchParams()
    form.append("username", email)
    form.append("password", password)
    const res = await fetch(apiUrl('v1/auth/login'), {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || "Login failed")
    }
    const data = await res.json()
    localStorage.setItem("token", data.access_token)
    localStorage.setItem("user_email", email)
    setTokenCookie(data.access_token)
    setUser({ email })
  }

  const signup = async (email: string, password: string) => {
    const res = await fetch(apiUrl('v1/auth/register'), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || "Signup failed")
    }
    // Auto-login after signup
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("user_email")
    localStorage.removeItem("selectedOutfitItems") // Clear selected items on logout
    // Remove cookie
    document.cookie = "token=; path=/; max-age=0"
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
