"use client"

import { useState } from "react"
import { Shirt } from "lucide-react"
import "keen-slider/keen-slider.min.css"
import { useKeenSlider } from "keen-slider/react"
import { Header } from "@/components/header"
import Link from "next/link"

export default function AboutPage() {
  // Fashion images for the carousel
  const fashionImages = [
    {
      src: "/about-images/male-1.png",
      alt: "Blue and white striped shirt with white jeans",
      title: "Urban Cool",
    },
    {
      "src": "/about-images/male-2.png",
      "alt": "Smart-casual outfit with black sweater, white shirt, jogger pants, and dress shoes",
      "title": "Modern Smartwear"
    },
    {
    "src": "/about-images/female-1.png",
    "alt": "Casual outfit with camel coat, coral blouse, ripped jeans, and black flats",
    "title": "Urban Casual"
    },
    {
      "src": "/about-images/female-2.png",
      "title": "Boho Casual",
      "alt": "White embroidered blouse with distressed denim shorts",
    },
    {
      "src": "/about-images/female-3.png",
      "title": "Retro Vibes",
      "alt": "Peach floral blouse and flared jeans",
    },
  ]

  const [sliderRef, instanceRef] = useKeenSlider({
    loop: true,
    slides: { perView: 1 }, // default for small screens
    breakpoints: {
      "(min-width: 600px)": {
        slides: { perView: 2 },
      },
      "(min-width: 900px)": {
        slides: { perView: 3 },
      },
      "(min-width: 1200px)": {
        slides: { perView: 4 }
      }
    },
  })

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Enhanced Geometric Background Pattern */}
      <div className="absolute inset-0 opacity-[0.03]">
        <svg className="w-full h-full" viewBox="0 0 1200 800" fill="none">
          <defs>
            <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
              <path d="M 80 0 L 0 0 0 80" fill="none" stroke="white" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          <path d="M0 0 L300 200 L600 50 L900 250 L1200 100" stroke="white" strokeWidth="0.5" fill="none" />
          <path
            d="M0 800 L250 600 L500 750 L750 550 L1000 700 L1200 500"
            stroke="white"
            strokeWidth="0.5"
            fill="none"
          />
          <path
            d="M0 400 L200 300 L400 450 L600 250 L800 400 L1000 200 L1200 350"
            stroke="white"
            strokeWidth="0.5"
            fill="none"
          />
        </svg>
      </div>

      <Header />

      <div className="relative z-10">
        {/* Hero Section */}
        <div className="container mx-auto px-6 pt-16 pb-8 text-center">
          {/* Collection Badge */}
          <div className="inline-flex items-center bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-full px-6 py-2 mb-12">
            <span className="text-sm text-gray-300 font-medium">AI-Powered Style Assistant 2024</span>
          </div>

          {/* Main Headline */}
          <div className="max-w-5xl mx-auto mb-8">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.1] mb-8 tracking-tight">
              Where style speaks, trends resonate,
              <br />
              <span className="text-gray-400">fashion flourishes</span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-400 max-w-3xl mx-auto leading-relaxed font-light">
              Unveiling a fashion destination where trends blend seamlessly with your
              <br />
              individual style aspirations. Discover today!
            </p>
          </div>

          {/* CTA Button */}
          <div className="mb-20">
            <Link href="/">
              <button className="inline-flex items-center bg-white text-black hover:bg-gray-100 rounded-full px-8 py-4 text-base font-semibold transition-all duration-300 group shadow-lg hover:shadow-xl">
                Upload & Generate
                <div className="ml-3 w-6 h-6 bg-black rounded-full flex items-center justify-center group-hover:translate-x-1 transition-transform">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              </button>
            </Link>
          </div>
        </div>

        {/* Fashion Carousel (Keen Slider) */}
        <div className="relative mb-20 max-w-[1600px] mx-auto px-4">
          <div ref={sliderRef} className="keen-slider">
            {fashionImages.map((image, idx) => (
              <div
                key={idx}
                className="keen-slider__slide"
                style={{ minWidth: 0 }}
              >
                <div
                  className="w-[260px] h-[500px] bg-gradient-to-br from-gray-700 to-gray-900 rounded-[2rem] overflow-hidden relative shadow-2xl flex flex-col justify-end cursor-pointer mx-auto"
                >
                  <img
                    src={image.src || "/placeholder.svg"}
                    alt={image.alt}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  {/* Always show title for all cards */}
                  <div className="absolute bottom-6 left-6 right-6">
                    <div className="bg-black/70 backdrop-blur-sm rounded-xl px-4 py-3 text-center">
                      <div className="text-white text-sm font-medium">{image.title}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {/* Navigation Arrows */}
          <button
            className="absolute left-0 top-1/2 -translate-y-1/2 z-30 w-12 h-12 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full flex items-center justify-center hover:bg-white/20 transition-all duration-200 group"
            onClick={() => instanceRef.current?.prev()}
            aria-label="Previous"
            type="button"
          >
            <span className="sr-only">Previous</span>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
          </button>
          <button
            className="absolute right-0 top-1/2 -translate-y-1/2 z-30 w-12 h-12 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full flex items-center justify-center hover:bg-white/20 transition-all duration-200 group"
            onClick={() => instanceRef.current?.next()}
            aria-label="Next"
            type="button"
          >
            <span className="sr-only">Next</span>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
          </button>
        </div>

        {/* Mission Section */}
        <div className="container mx-auto px-6 py-16">
          <div className="text-center max-w-4xl mx-auto mb-16">
            <div className="flex items-center justify-center mb-6">
              <Shirt className="w-10 h-10 text-white mr-3" />
              <h2 className="text-4xl font-bold">About OutfitPredict</h2>
            </div>
            <p className="text-xl text-gray-400 leading-relaxed mb-8">
              We believe that everyone deserves to look and feel their best. Our AI-powered platform analyzes your
              wardrobe, understands your style preferences, and creates personalized outfit recommendations that reflect
              your unique personality and lifestyle.
            </p>
          </div>

          {/* Stats Section */}
          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto mb-16">
            <div className="text-center">
              <div className="text-4xl font-bold text-white mb-2">N+</div>
              <div className="text-gray-400 text-lg">Outfits Generated</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-white mb-2">K+</div>
              <div className="text-gray-400 text-lg">Happy Users</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-white mb-2">M%</div>
              <div className="text-gray-400 text-lg">Style Accuracy</div>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700/50 rounded-3xl p-8">
              <h3 className="text-2xl font-semibold mb-4 text-white">Smart Technology</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                Advanced computer vision and machine learning algorithms analyze your clothing items to understand
                colors, patterns, styles, and compatibility for perfect outfit combinations.
              </p>
            </div>
            <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700/50 rounded-3xl p-8">
              <h3 className="text-2xl font-semibold mb-4 text-white">Personal Style</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                Every recommendation is tailored to your personal taste, body type, and lifestyle, ensuring you always
                look authentically you with confidence and style.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 