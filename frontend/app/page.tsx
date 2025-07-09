"use client"

import React, { useState, useCallback, useRef } from "react"
import { Upload, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/header"
import { getApiBaseUrl, apiUrl } from "@/lib/utils"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"

export default function OutfitGeneratorMain() {
  const [files, setFiles] = useState<File[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [isMessageFadingOut, setIsMessageFadingOut] = useState(false)
  const fadeOutTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [recommendations, setRecommendations] = useState<any[] | null>(null)
  const [showRecommendations, setShowRecommendations] = useState(false)
  const [loadingRecommendations, setLoadingRecommendations] = useState(false)
  const [recommendationError, setRecommendationError] = useState<string | null>(null)
  const [wardrobeImages, setWardrobeImages] = useState<any[]>([])
  const [wardrobeLoading, setWardrobeLoading] = useState(true)
  const { user, loading } = useAuth()
  const router = useRouter()

  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;

  // Fetch wardrobe images on mount
  React.useEffect(() => {
    if (!loading && !user) {
      router.replace("/login")
      return
    }
    const fetchImages = async () => {
      setWardrobeLoading(true)
      try {
        const res = await fetch(apiUrl('v1/images/'), {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        if (!res.ok) throw new Error("Failed to fetch profile images")
        const data = await res.json()
        setWardrobeImages(data)
      } catch (err) {
        setWardrobeImages([])
      } finally {
        setWardrobeLoading(false)
      }
    }
    fetchImages()
  }, [user, router, token, loading])

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

  const uploadImage = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    try {
      const response = await fetch(apiUrl('v1/images/'), {
        method: "POST",
        body: formData,
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (response.ok) {
        const result = await response.json()
        showUploadMessage(`Image "${file.name}" uploaded successfully!`)
        setWardrobeImages((prev: any[]) => [result, ...prev])
      } else {
        showUploadMessage(`Failed to upload "${file.name}".`)
      }
    } catch (error) {
      showUploadMessage(`Error uploading "${file.name}".`)
    }
  }, [showUploadMessage, token])

  // Concurrency-limited upload queue
  const MAX_CONCURRENT_UPLOADS = 10;
  const uploadQueueRef = useRef<File[]>([]);
  const activeUploadsRef = useRef(0);

  const processQueue = useCallback(() => {
    if (activeUploadsRef.current >= MAX_CONCURRENT_UPLOADS || uploadQueueRef.current.length === 0) return;
    while (activeUploadsRef.current < MAX_CONCURRENT_UPLOADS && uploadQueueRef.current.length > 0) {
      const file = uploadQueueRef.current.shift();
      if (file) {
        activeUploadsRef.current++;
        uploadImage(file).finally(() => {
          activeUploadsRef.current--;
          processQueue();
        });
      }
    }
  }, [uploadImage]);

  const enqueueFiles = useCallback((files: File[]) => {
    uploadQueueRef.current.push(...files);
    processQueue();
  }, [processQueue]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter((file) => ["image/jpeg", "image/png"].includes(file.type));
      enqueueFiles(selectedFiles);
    }
  }, [enqueueFiles]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter((file) => ["image/jpeg", "image/png"].includes(file.type));
    enqueueFiles(droppedFiles);
  }, [enqueueFiles]);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleGenerateOutfits = useCallback(async () => {
    let imagesToSend: File[] = files
    // If no files uploaded, use wardrobe images
    if (imagesToSend.length === 0 && wardrobeImages.length > 0) {
      setLoadingRecommendations(true)
      setRecommendationError(null)
      try {
        const blobs = await Promise.all(
          wardrobeImages.map(async (img: any, idx: number) => {
            const res = await fetch(img.url)
            const blob = await res.blob()
            return new File([blob], img.description || `wardrobe_${idx}.jpg`, { type: blob.type })
          })
        )
        imagesToSend = blobs
      } catch (err) {
        setRecommendationError("Failed to load wardrobe images for outfit generation.")
        setLoadingRecommendations(false)
        return
      }
    }
    if (imagesToSend.length === 0) {
      showUploadMessage("Please upload at least one image to your profile.")
      return
    }
    setLoadingRecommendations(true)
    setRecommendationError(null)
    try {
      const formData = new FormData()
      imagesToSend.forEach((file) => formData.append("files", file))
      const response = await fetch(apiUrl('v1/outfits/search-similar/'), {
        method: "POST",
        body: formData,
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (!response.ok) throw new Error("Failed to generate outfits")
      const recs = await response.json()
      // Fetch all wardrobe images
      const imagesRes = await fetch(apiUrl('v1/images/'), {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (!imagesRes.ok) throw new Error("Failed to fetch profile images")
      const images = await imagesRes.json()
      // Attach wardrobe image URLs to recommendations
      const recsWithUrls = recs.map((rec: any) => ({
        ...rec,
        matchesWithUrls: rec.matches.map((match: any) => {
          const wardrobeImage = images.find((img: any) => img.id === match.wardrobe_image_id)
          return {
            ...match,
            wardrobe_image_url: wardrobeImage?.url,
            wardrobe_image_description: wardrobeImage?.description,
            wardrobe_image_object_name: wardrobeImage?.object_name,
          }
        })
      }))
      setRecommendations(recsWithUrls)
      setShowRecommendations(true)
      setLoadingRecommendations(false)
    } catch (err: any) {
      setRecommendationError(err.message || "Unknown error")
      setLoadingRecommendations(false)
    }
  }, [files, wardrobeImages, token, showUploadMessage])

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

      <div className="relative z-10 container mx-auto px-6 py-16">
        {/* Page Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-full px-6 py-2 mb-8">
            <span className="text-sm text-gray-300 font-medium">AI-Powered Style Generator</span>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight">
            Generate Your Perfect
            <br />
            <span className="text-gray-400">Outfit Combinations</span>
          </h1>

          <p className="text-xl text-gray-400 max-w-3xl mx-auto leading-relaxed font-light mb-8">
            Upload photos of your clothing items and let our AI create personalized outfit recommendations that match
            your style
          </p>
        </div>

        {/* Upload Section */}
        <div className="max-w-4xl mx-auto mb-16">
          <div className="relative mb-12">
            <div
              className={`border-2 border-dashed rounded-3xl p-20 text-center transition-all duration-300 ${
                isDragOver
                  ? "border-white/50 bg-gray-800/30 scale-[1.02]"
                  : "border-gray-600/50 bg-gray-900/20 backdrop-blur-sm hover:border-gray-500/50 hover:bg-gray-800/25"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="w-24 h-24 bg-gray-800/50 rounded-3xl flex items-center justify-center mx-auto mb-8">
                <Upload className="w-12 h-12 text-gray-300" />
              </div>

              <h2 className="text-3xl font-semibold text-white mb-6">Upload Your Clothing Images</h2>

              <p className="text-gray-400 mb-10 text-xl leading-relaxed max-w-2xl mx-auto">
                Drag and drop your photos here, or click to browse your files
                <br />
                <span className="text-base text-gray-500 mt-2 block">
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
              />

              <label htmlFor="file-upload">
                <Button
                  variant="outline"
                  className="cursor-pointer rounded-full border-2 border-gray-500 bg-transparent text-white hover:bg-white hover:text-black transition-all duration-300 px-12 py-5 text-lg font-semibold shadow-lg hover:shadow-xl"
                  asChild
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
              disabled={loadingRecommendations}
            >
              <Sparkles className="w-7 h-7" />
              {loadingRecommendations ? "Generating AI Outfits..." : "Generate AI Outfits"}
            </Button>

            {!loadingRecommendations && (
              <p className="text-gray-500 mt-4 text-sm">
                Our AI will analyze your clothing items and create perfect outfit combinations
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
            <h3 className="text-2xl font-semibold mb-2">Creating Your Outfits</h3>
            <p className="text-gray-400">
              Our AI is analyzing your wardrobe and generating personalized recommendations...
            </p>
          </div>
        )}

        {/* Error State */}
        {recommendationError && (
          <div className="text-center py-12">
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 max-w-md mx-auto">
              <h3 className="text-xl font-semibold text-red-400 mb-2">Generation Failed</h3>
              <p className="text-red-300">{recommendationError}</p>
            </div>
          </div>
        )}
      </div>

      {/* Recommendations Modal */}
      {showRecommendations && recommendations && (
        <div
          className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowRecommendations(false)}
        >
          <div
            className="bg-gray-900/95 backdrop-blur-sm border border-gray-700/50 rounded-3xl p-10 max-w-6xl w-full max-h-[90vh] overflow-auto shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="absolute top-8 right-8 text-gray-400 hover:text-white text-3xl font-light transition-colors w-12 h-12 flex items-center justify-center rounded-full hover:bg-gray-800/50"
              onClick={() => setShowRecommendations(false)}
            >
              ×
            </button>

            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold mb-4 text-white">Your AI-Generated Outfits</h2>
              <p className="text-gray-400 text-lg">Here are personalized outfit combinations based on your wardrobe</p>
            </div>

            {recommendations.length === 0 ? (
              <div className="text-center text-gray-400 text-xl py-16">
                <div className="w-16 h-16 bg-gray-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-8 h-8 text-gray-500" />
                </div>
                No outfit recommendations found. Try uploading more clothing items.
              </div>
            ) : (
              <div className="space-y-12">
                {recommendations.map((rec, idx) => (
                  <div key={idx} className="bg-gray-800/30 rounded-3xl p-8 border border-gray-700/30">
                    <div className="flex flex-col lg:flex-row gap-10 items-center">
                      <div className="relative">
                        <img
                          src={rec.outfit.url || "/placeholder.svg"}
                          alt="Generated Outfit"
                          className="w-72 h-72 object-cover rounded-3xl border border-gray-600/50 shadow-lg"
                        />
                        <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-sm rounded-full px-4 py-2">
                          <span className="text-white text-sm font-medium">Outfit #{idx + 1}</span>
                        </div>
                      </div>

                      <div className="flex-1">
                        <h3 className="text-2xl font-bold text-white mb-6">Matched Wardrobe Items</h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                          {rec.matchesWithUrls && rec.matchesWithUrls.length > 0 ? (
                            rec.matchesWithUrls.map((match: any, i: number) => (
                              <div key={i} className="text-center">
                                {match.wardrobe_image_url ? (
                                  <img
                                    src={match.wardrobe_image_url || "/placeholder.svg"}
                                    alt={match.wardrobe_image_description || "Wardrobe item"}
                                    className="w-32 h-32 object-cover rounded-2xl border border-gray-600/50 shadow-md mx-auto mb-3"
                                  />
                                ) : (
                                  <div className="w-32 h-32 bg-gray-800/50 rounded-2xl flex items-center justify-center text-xs text-gray-500 border border-gray-600/50 mx-auto mb-3">
                                    No image
                                  </div>
                                )}
                                <p className="text-sm text-gray-300 font-medium max-w-[8rem] mx-auto truncate">
                                  {match.wardrobe_image_description || match.wardrobe_image_object_name}
                                </p>
                              </div>
                            ))
                          ) : (
                            <div className="col-span-full text-center text-gray-500 text-lg py-8">
                              No wardrobe items matched for this outfit.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
