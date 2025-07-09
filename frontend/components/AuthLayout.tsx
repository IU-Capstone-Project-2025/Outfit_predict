"use client"

import React from "react"
import Link from "next/link"

interface AuthLayoutProps {
  heading: string
  headingColor: string
  buttonText: string
  buttonGradient: string
  buttonHoverGradient: string
  inputFocusRing: string
  backgroundGradient: string
  children: React.ReactNode
  bottomText: string
  bottomLink: string
  bottomLinkHref: string
  bottomLinkColor: string
}

export default function AuthLayout({
  heading,
  headingColor,
  buttonText,
  buttonGradient,
  buttonHoverGradient,
  inputFocusRing,
  backgroundGradient,
  children,
  bottomText,
  bottomLink,
  bottomLinkHref,
  bottomLinkColor,
}: AuthLayoutProps) {
  return (
    <div className={`min-h-screen flex items-center justify-center ${backgroundGradient}`}>
      <div className="bg-white rounded-3xl shadow-xl p-10 max-w-md w-full border border-gray-100">
        <h2 className={`text-3xl font-bold mb-6 text-center ${headingColor}`}>{heading}</h2>
        {children}
        <div className="mt-6 text-center text-gray-600">
          {bottomText} <Link href={bottomLinkHref} className={`${bottomLinkColor} font-semibold hover:underline`}>{bottomLink}</Link>
        </div>
      </div>
    </div>
  )
} 