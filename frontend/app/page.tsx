"use client"

import React, { useState, useCallback, useRef } from "react"
import { Upload, Sparkles, Heart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/header"
import { getApiBaseUrl, apiUrl, fetchWithAuth } from "@/lib/utils"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import {
  ImagePreviewModal,
  ProtectedImage,
} from "@/components/ImagePreviewModal"
import { ImageWithPlaceholder } from "@/components/ImageWithPlaceholder"
import { RecommendationsModal } from "@/components/RecommendationsModal"

export default function OutfitGeneratorMain() {
  const [files, setFiles] = useState<File[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [isMessageFadingOut, setIsMessageFadingOut] = useState(false)
  const fadeOutTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [recommendations, setRecommendations] = useState<any[] | null>(null)
  const [loadingRecommendations, setLoadingRecommendations] = useState(false)
  const [recommendationError, setRecommendationError] = useState<string | null>(
    null
  )
  const { user, loading } = useAuth()
  const router = useRouter()
  const [previewImage, setPreviewImage] = useState<{
    src: string
    thumbnailSrc?: string
    alt?: string
    description?: string
  } | null>(null)
  const [savedOutfits, setSavedOutfits] = useState<Set<string>>(new Set())
  const [savingOutfits, setSavingOutfits] = useState<Set<string>>(new Set())
  const [showRecommendations, setShowRecommendations] = useState(false)

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null

  // Helper to handle logout and redirect
  const handle401Logout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token")
      localStorage.removeItem("user_email")
      localStorage.removeItem("selectedOutfitItems")
    }
    router.replace("/login")
  }

  // Save outfit function
  const saveOutfit = useCallback(
    async (recommendation: any) => {
      if (!user || !recommendation) return

      const outfitId = recommendation.outfit.id
      setSavingOutfits(prev => new Set(prev).add(outfitId))

      try {
        // Ensure matches only contain the fields expected by the backend
        const filteredMatches = recommendation.recommendation.matches.map(
          (match: any) => {
            const isWardrobeItem =
              match.wardrobe_image_object_name &&
              match.wardrobe_image_index !== undefined

            const baseItem = {
              outfit_item_id: match.outfit_item_id,
              score: match.score,
            }

            if (isWardrobeItem) {
              return {
                ...baseItem,
                wardrobe_image_index: match.wardrobe_image_index,
                wardrobe_image_object_name: match.wardrobe_image_object_name,
                clothing_type: match.clothing_type,
              }
            } else {
              return {
                ...baseItem,
                clothing_type: match.clothing_type,
                wardrobe_image_index: null,
                wardrobe_image_object_name: null,
                external_image_url: match.suggested_item_image_link,
                suggested_item_product_link: match.suggested_item_product_link,
              }
            }
          }
        )

        const saveData = {
          outfit_id: outfitId,
          completeness_score: recommendation.recommendation.completeness_score,
          matches: filteredMatches,
        }

        const response = await fetchWithAuth(
          apiUrl("v1/saved-outfits/"),
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(saveData),
          },
          handle401Logout
        )

        if (!response.ok) {
          const errorData = await response.json()
          if (response.status === 409) {
            throw new Error("This outfit is already saved!")
          }
          throw new Error(errorData.detail || "Failed to save outfit")
        }

        setSavedOutfits(prev => new Set(prev).add(outfitId))
        showUploadMessage("Outfit saved successfully!")
      } catch (err: any) {
        console.error("Error saving outfit:", err)
        showUploadMessage(
          err.message || "Failed to save outfit. Please try again."
        )
      } finally {
        setSavingOutfits(prev => {
          const newSet = new Set(prev)
          newSet.delete(outfitId)
          return newSet
        })
      }
    },
    [user, token, router]
  )

  const showUploadMessage = useCallback((message: string) => {
    if (fadeOutTimeoutRef.current) {
      clearTimeout(fadeOutTimeoutRef.current) // Clear existing timeout if any
    }
    setUploadMessage(message)
    setIsMessageFadingOut(false)

    fadeOutTimeoutRef.current = setTimeout(() => {
      setIsMessageFadingOut(true)
      setTimeout(() => {
        setUploadMessage(null)
        setIsMessageFadingOut(false)
      }, 500)
    }, 2500)
  }, [])

  const uploadImage = useCallback(
    async (file: File) => {
      if (!user) {
        return
      }
      const formData = new FormData()
      formData.append("file", file)
      try {
        const response = await fetch(apiUrl("v1/images/"), {
          method: "POST",
          body: formData,
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        if (response.ok) {
          const result = await response.json()
          showUploadMessage(`Image "${file.name}" uploaded successfully!`)
        } else {
          showUploadMessage(`Failed to upload "${file.name}".`)
        }
      } catch (error) {
        showUploadMessage(`Error uploading "${file.name}".`)
      }
    },
    [showUploadMessage, token, user]
  )

  // Concurrency-limited upload queue
  const MAX_CONCURRENT_UPLOADS = 10
  const uploadQueueRef = useRef<File[]>([])
  const activeUploadsRef = useRef(0)

  const processQueue = useCallback(() => {
    if (
      activeUploadsRef.current >= MAX_CONCURRENT_UPLOADS ||
      uploadQueueRef.current.length === 0
    )
      return
    while (
      activeUploadsRef.current < MAX_CONCURRENT_UPLOADS &&
      uploadQueueRef.current.length > 0
    ) {
      const file = uploadQueueRef.current.shift()
      if (file) {
        activeUploadsRef.current++
        uploadImage(file).finally(() => {
          activeUploadsRef.current--
          processQueue()
        })
      }
    }
  }, [uploadImage])

  const enqueueFiles = useCallback(
    (files: File[]) => {
      uploadQueueRef.current.push(...files)
      processQueue()
    },
    [processQueue]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        const selectedFiles = Array.from(e.target.files).filter(file =>
          ["image/jpeg", "image/png"].includes(file.type)
        )
        enqueueFiles(selectedFiles)
      }
    },
    [enqueueFiles]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragOver(false)
      const droppedFiles = Array.from(e.dataTransfer.files).filter(file =>
        ["image/jpeg", "image/png"].includes(file.type)
      )
      enqueueFiles(droppedFiles)
    },
    [enqueueFiles]
  )

  const removeFile = useCallback((index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleGenerateOutfits = useCallback(async () => {
    if (!user) {
      return
    }
    setLoadingRecommendations(true)
    setRecommendationError(null)
    try {
      const selectedObjectNames = JSON.parse(
        localStorage.getItem("selectedOutfitItems") || "[]"
      )

      let requestBody: { object_names?: string[]; image_ids?: string[] } = {}
      let endpoint = "v1/outfits/search-similar/"

      if (selectedObjectNames.length > 0) {
        requestBody = { object_names: selectedObjectNames }
        endpoint = "v1/outfits/search-similar-subset/"
      }

      // 1. Call the backend to generate recommendations
      const response = await fetch(apiUrl(endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(requestBody),
      })
      if (!response.ok) throw new Error("Failed to generate outfits")
      const recs = await response.json()
      // 2. For each match, fetch the wardrobe image URL from the new endpoint
      const recsWithUrls = await Promise.all(
        recs.map(async (rec: any) => {
          const matchesSrc = rec.recommendation?.matches || []
          const matchesWithUrls = await Promise.all(
            matchesSrc.map(async (match: any) => {
              let wardrobe_image_url = undefined
              let wardrobe_image_thumbnail_url = undefined
              let wardrobe_image_description = undefined
              if (match.wardrobe_image_object_name) {
                try {
                  const urlRes = await fetch(
                    apiUrl(
                      `v1/utilities/${encodeURIComponent(
                        match.wardrobe_image_object_name
                      )}/url`
                    ),
                    {
                      headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                      },
                    }
                  )
                  if (urlRes.ok) {
                    const urlData = await urlRes.json()
                    wardrobe_image_url = urlData.url
                    wardrobe_image_thumbnail_url = urlData.thumbnail_url
                    wardrobe_image_description = urlData.description
                  }
                } catch (e) {
                  // fallback to undefined
                }
              }
              return {
                ...match,
                wardrobe_image_url: wardrobe_image_url || "/placeholder.svg",
                wardrobe_image_thumbnail_url: wardrobe_image_thumbnail_url,
                wardrobe_image_description: wardrobe_image_description,
              }
            })
          )
          return {
            ...rec,
            matchesWithUrls,
          }
        })
      )
      setRecommendations(recsWithUrls)
      setShowRecommendations(true)

      // Check which outfits are already saved
      try {
        const savedResponse = await fetchWithAuth(
          apiUrl("v1/saved-outfits/"),
          {},
          handle401Logout
        )
        if (savedResponse.ok) {
          const savedData = await savedResponse.json()
          const savedIds = new Set<string>(
            savedData.map((saved: any) => saved.outfit_id)
          )
          setSavedOutfits(savedIds)
        }
      } catch (err) {
        console.warn("Failed to fetch saved outfits:", err)
      }
    } catch (err) {
      setRecommendationError("Failed to generate outfits. Please try again.")
    } finally {
      setLoadingRecommendations(false)
    }
  }, [showUploadMessage, token, user, handle401Logout])

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Enhanced Geometric Background Pattern */}
      <div className="absolute inset-0 opacity-[0.03]">
        <svg className="w-full h-full" viewBox="0 0 1200 800" fill="none">
          <defs>
            <pattern
              id="grid"
              width="80"
              height="80"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 80 0 L 0 0 0 80"
                fill="none"
                stroke="white"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          <path
            d="M0 0 L300 200 L600 50 L900 250 L1200 100"
            stroke="white"
            strokeWidth="0.5"
            fill="none"
          />
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

      {/* Image Preview Modal rendered at the top level, outside recommendations modal overlay */}
      <ImagePreviewModal
        open={!!previewImage}
        onClose={() => setPreviewImage(null)}
        src={previewImage?.src || ""}
        thumbnailSrc={previewImage?.thumbnailSrc}
        alt={previewImage?.alt}
        description={previewImage?.description}
        token={token}
      />

      <RecommendationsModal
        show={showRecommendations && !previewImage}
        recommendations={recommendations || []}
        onClose={() => setShowRecommendations(false)}
        onSave={saveOutfit}
        onPreview={setPreviewImage}
        savingOutfits={savingOutfits}
        savedOutfits={savedOutfits}
        token={token}
      />

      <div className="relative z-10 container mx-auto px-4 py-12">
        {!user ? (
          <div className="text-center text-xl text-gray-300 py-24">
            You need to log in to upload images and generate outfits.
            <div className="mt-8 flex justify-center gap-4">
              <a
                href="/login"
                className="text-gray-300 hover:text-white transition-colors font-medium px-8 py-3 rounded-full"
              >
                Login
              </a>
              <a
                href="/signup"
                className="bg-white text-black hover:bg-gray-100 rounded-full px-8 py-3 text-lg font-semibold transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                Sign Up
              </a>
            </div>
          </div>
        ) : (
          <>
            {/* Page Header */}
            <div className="text-center mb-16">
              <div className="inline-flex items-center bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-full px-6 py-2 mb-8">
                <span className="text-sm text-gray-300 font-medium">
                  AI-Powered Style Generator
                </span>
              </div>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight">
                Generate Your Perfect
                <br />
                Outfit Combinations
              </h1>

              <p className="text-xl text-gray-400 max-w-3xl mx-auto leading-relaxed font-light mb-8">
                Upload photos of your clothing items and let our AI create
                personalized outfit recommendations that match your style
              </p>
            </div>

            {/* Upload Section */}
            <div className="max-w-4xl mx-auto mb-16">
              <div className="relative mb-12">
                <div
                  className={`border-2 border-dashed rounded-3xl py-8 px-4 sm:py-10 sm:px-8 md:py-12 md:px-12 text-center transition-all duration-300 w-full max-w-xs sm:max-w-md md:max-w-xl lg:max-w-2xl mx-auto ${
                    isDragOver
                      ? "border-white/50 bg-gray-800/30 scale-[1.02]"
                      : "border-gray-600/50 bg-gray-900/20 backdrop-blur-sm hover:border-gray-500/50 hover:bg-gray-800/25"
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <div className="w-12 h-12 sm:w-16 sm:h-16 md:w-20 md:h-20 bg-gray-800/50 rounded-3xl flex items-center justify-center mx-auto mb-6">
                    <Upload className="w-7 h-7 sm:w-9 sm:h-9 md:w-10 md:h-10 text-gray-300" />
                  </div>

                  <h2 className="text-xl sm:text-2xl md:text-3xl font-semibold text-white mb-4">
                    Upload Your Clothing Images
                  </h2>

                  <p className="text-gray-400 mb-6 text-base sm:text-lg md:text-xl leading-relaxed max-w-2xl mx-auto">
                    Drag and drop your photos here, or click to browse your
                    files
                    <br />
                    <span className="text-xs sm:text-sm md:text-base text-gray-500 mt-2 block">
                      Supports JPG and PNG formats • Multiple files allowed
                    </span>
                  </p>

                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                    disabled={!user}
                  />

                  <label htmlFor="file-upload" className="block w-full">
                    <Button
                      variant="outline"
                      className="cursor-pointer rounded-full border-2 border-gray-500 bg-transparent text-white hover:bg-white hover:text-black transition-all duration-300 w-full max-w-xs mx-auto px-6 py-4 sm:px-10 sm:py-5 text-base sm:text-lg font-semibold shadow-lg hover:shadow-xl"
                      asChild
                      disabled={!user}
                    >
                      <span>Choose Files</span>
                    </Button>
                  </label>
                </div>

                {/* Upload Message */}
                {uploadMessage && (
                  <div
                    className={`absolute -bottom-20 left-1/2 transform -translate-x-1/2 bg-green-600/90 backdrop-blur-sm text-white px-8 py-4 rounded-2xl shadow-lg transition-opacity duration-500 ${
                      isMessageFadingOut ? "opacity-0" : "opacity-100"
                    } whitespace-nowrap text-lg font-medium`}
                  >
                    {uploadMessage}
                  </div>
                )}
              </div>

              {/* Generate Button */}
              <div className="text-center">
                <Button
                  className="bg-white text-black hover:bg-gray-100 rounded-full px-20 py-6 text-xl font-bold transition-all duration-300 group flex items-center gap-4 shadow-xl hover:shadow-2xl mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={handleGenerateOutfits}
                  disabled={loadingRecommendations || !user}
                >
                  <Sparkles className="w-7 h-7" />
                  {loadingRecommendations
                    ? "Generating AI Outfits..."
                    : "Generate AI Outfits"}
                </Button>

                {!loadingRecommendations && (
                  <p className="text-gray-500 mt-4 text-sm">
                    Our AI will analyze your clothing items and create perfect
                    outfit combinations
                  </p>
                )}
              </div>
            </div>

            {/* Loading State */}
            {loadingRecommendations && (
              <div className="text-center py-16">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-800/50 rounded-full mb-6">
                  <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                </div>
                <h3 className="text-2xl font-semibold mb-2">
                  Creating Your Outfits
                </h3>
                <p className="text-gray-400">
                  Our AI is analyzing your wardrobe and generating
                  personalized recommendations...
                </p>
              </div>
            )}

            {/* Error State */}
            {recommendationError && (
              <div className="text-center py-12">
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 max-w-md mx-auto">
                  <h3 className="text-xl font-semibold text-red-400 mb-2">
                    Generation Failed
                  </h3>
                  <p className="text-red-300">{recommendationError}</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
