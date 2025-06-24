"use client"

import React, { useState, useCallback, useRef } from "react"
import { Upload, X, Shirt, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/header"
import { getApiBaseUrl } from "@/lib/utils"
import Link from "next/link"
import { useRouter } from "next/navigation"

export default function OutfitGeneratorLanding() {
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

  // Fetch wardrobe images on mount
  React.useEffect(() => {
    const fetchImages = async () => {
      setWardrobeLoading(true)
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/images/`)
        if (!res.ok) throw new Error("Failed to fetch wardrobe images")
        const data = await res.json()
        setWardrobeImages(data)
      } catch (err) {
        setWardrobeImages([])
      } finally {
        setWardrobeLoading(false)
      }
    }
    fetchImages()
  }, [])

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
    // You can also append a description if needed, e.g., formData.append("description", "My clothing item")

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/images/`, {
        method: "POST",
        body: formData,
      })

      if (response.ok) {
        const result = await response.json()
        console.log("Upload successful:", result)
        showUploadMessage(`Image "${file.name}" uploaded successfully!`)
      } else {
        console.error("Upload failed:", response.statusText)
        showUploadMessage(`Failed to upload "${file.name}".`)
      }
    } catch (error) {
      console.error("Error during upload:", error)
      showUploadMessage(`Error uploading "${file.name}".`)
    }
  }, [showUploadMessage])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const droppedFiles = Array.from(e.dataTransfer.files).filter((file) => file.type === "image/jpeg")
    droppedFiles.forEach(uploadImage) // Upload each dropped image
  }, [uploadImage])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter((file) => file.type === "image/jpeg")
      selectedFiles.forEach(uploadImage) // Upload each selected image
    }
  }, [uploadImage])

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleGenerateOutfits = useCallback(async () => {
    let imagesToSend: File[] = files
    // If no files uploaded, use wardrobe images
    if (imagesToSend.length === 0 && wardrobeImages.length > 0) {
      // Fetch each wardrobe image as blob and convert to File
      setLoadingRecommendations(true)
      setRecommendationError(null)
      try {
        const blobs = await Promise.all(
          wardrobeImages.map(async (img: any, idx: number) => {
            const res = await fetch(img.url)
            const blob = await res.blob()
            // Try to keep the filename unique and extension correct
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
      showUploadMessage("Please upload at least one image to your wardrobe.")
      return
    }
    setLoadingRecommendations(true)
    setRecommendationError(null)
    try {
      const formData = new FormData()
      imagesToSend.forEach((file) => formData.append("files", file))
      const response = await fetch(`${getApiBaseUrl()}/api/v1/outfits/search-similar/`, {
        method: "POST",
        body: formData,
      })
      if (!response.ok) throw new Error("Failed to generate outfits")
      const recs = await response.json()
      // Fetch all wardrobe images
      const imagesRes = await fetch(`${getApiBaseUrl()}/api/v1/images/`)
      if (!imagesRes.ok) throw new Error("Failed to fetch wardrobe images")
      const images = await imagesRes.json()
      // Attach wardrobe image URLs to recommendations
      const recsWithImages = recs.map((rec: any) => {
        const matchesWithUrls = (rec.recommendation?.matches || []).map((match: any) => {
          const wardrobeImage = images.find((img: any) => img.object_name === match.wardrobe_image_object_name)
          return {
            ...match,
            wardrobe_image_url: wardrobeImage ? wardrobeImage.url : null,
            wardrobe_image_description: wardrobeImage ? wardrobeImage.description : null,
          }
        })
        return {
          ...rec,
          matchesWithUrls,
        }
      })
      setRecommendations(recsWithImages)
      setShowRecommendations(true)
    } catch (err: any) {
      setRecommendationError(err.message || "Unknown error")
    } finally {
      setLoadingRecommendations(false)
    }
  }, [files, wardrobeImages, showUploadMessage])

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 relative overflow-hidden">
        {/* Animated Background Elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 left-10 w-32 h-32 bg-purple-200/30 rounded-full animate-float-slow"></div>
          <div className="absolute top-40 right-20 w-24 h-24 bg-pink-200/30 rounded-full animate-float-medium"></div>
          <div className="absolute bottom-32 left-1/4 w-40 h-40 bg-blue-200/20 rounded-full animate-float-slow"></div>
          <div className="absolute bottom-20 right-1/3 w-28 h-28 bg-purple-300/25 rounded-full animate-float-fast"></div>
          <div className="absolute top-1/2 left-1/2 w-36 h-36 bg-pink-300/20 rounded-full animate-float-medium transform -translate-x-1/2 -translate-y-1/2"></div>
        </div>

        <div className="relative z-10 container mx-auto px-4 py-12">
          {/* Header */}
          <div className="text-center mb-4">
            <div className="flex items-center justify-center mb-4">
              <Shirt className="w-8 h-8 text-purple-600 mr-2" />
              <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                OutfitPredict
              </h1>
            </div>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Upload photos of your clothes and get personalized outfit recommendations powered by AI
            </p>
          </div>

          {/* Add View My Wardrobe button below the title and description */}
          <div className="flex justify-center mb-16">
            <Link href="/wardrobe">
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-pink-600 hover:to-purple-600 text-white shadow-lg hover:shadow-xl transition-all duration-200 px-6 py-3 rounded-xl">
                View My Wardrobe
              </Button>
            </Link>
          </div>

          {/* Upload Area */}
          <div className="max-w-2xl mx-auto mb-8 relative">
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                isDragOver
                  ? "border-purple-400 bg-purple-50 scale-105"
                  : "border-gray-300 bg-white/50 backdrop-blur-sm hover:border-purple-300 hover:bg-purple-50/50"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">Upload Your Clothing Images</h3>
              <p className="text-gray-500 mb-4">Drag and drop your photos here, or click to browse</p>
              <input
                type="file"
                accept="image/jpeg"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload">
                <Button variant="outline" className="cursor-pointer rounded-xl border border-gray-400 bg-white" asChild>
                  <span>Choose Files</span>
                </Button>
              </label>
              <p className="text-xs text-gray-400 mt-2">Supports JPG format only</p>
            </div>

            {/* Upload Message */}
            {uploadMessage && (
              <div
                className={`absolute bottom-[-50px] left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-xl shadow-lg transition-opacity duration-500 ${isMessageFadingOut ? 'opacity-0' : 'opacity-100'} whitespace-nowrap`}
              >
                {uploadMessage}
              </div>
            )}

            {/* Generate Outfits Button */}
            <div className="flex justify-center mt-8">
              <Button
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-pink-600 hover:to-purple-600 text-white shadow-lg hover:shadow-xl transition-all duration-200 px-6 py-3 rounded-xl flex items-center gap-2"
                onClick={handleGenerateOutfits}
                disabled={loadingRecommendations}
              >
                <Sparkles className="w-5 h-5 mr-2" />
                {loadingRecommendations ? "Generating..." : "Generate Outfits"}
              </Button>
            </div>
          </div>

          {/* Features */}
          <div className="max-w-4xl mx-auto mt-16 grid md:grid-cols-3 gap-8">
            <div className="text-center p-6 bg-white/30 backdrop-blur-sm rounded-xl">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Upload className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">Easy Upload</h3>
              <p className="text-gray-600 text-sm">Simply drag and drop or click to upload photos of your clothes</p>
            </div>
            <div className="text-center p-6 bg-white/30 backdrop-blur-sm rounded-xl">
              <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-6 h-6 text-pink-600" />
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">AI-Powered</h3>
              <p className="text-gray-600 text-sm">
                Our AI analyzes your clothes and creates stylish outfit combinations
              </p>
            </div>
            <div className="text-center p-6 bg-white/30 backdrop-blur-sm rounded-xl">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shirt className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">Personalized</h3>
              <p className="text-gray-600 text-sm">Get outfit suggestions tailored to your style and wardrobe</p>
            </div>
          </div>

          {/* Recommendations Modal */}
          {showRecommendations && recommendations && (
            <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setShowRecommendations(false)}>
              <div className="bg-white rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-auto shadow-2xl relative" onClick={e => e.stopPropagation()}>
                <button className="absolute top-4 right-4 text-gray-400 hover:text-gray-700 text-2xl" onClick={() => setShowRecommendations(false)}>&times;</button>
                <h2 className="text-2xl font-bold mb-6 text-center">Recommended Outfits</h2>
                {recommendations.length === 0 && <div className="text-center text-gray-500">No recommendations found.</div>}
                {recommendations.map((rec, idx) => (
                  <div key={idx} className="mb-8 border-b pb-6 last:border-b-0 last:pb-0">
                    <div className="flex flex-col md:flex-row gap-6 items-center">
                      <img src={rec.outfit.url} alt="Outfit" className="w-40 h-40 object-cover rounded-xl border" />
                      <div className="flex-1">
                        <div className="mb-2 font-semibold text-lg">Matched Wardrobe Items:</div>
                        <div className="flex flex-wrap gap-4">
                          {rec.matchesWithUrls && rec.matchesWithUrls.length > 0 ? (
                            rec.matchesWithUrls.map((match: any, i: number) => (
                              <div key={i} className="flex flex-col items-center">
                                {match.wardrobe_image_url ? (
                                  <img src={match.wardrobe_image_url} alt={match.wardrobe_image_description || "Wardrobe item"} className="w-20 h-20 object-cover rounded-lg border" />
                                ) : (
                                  <div className="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center text-xs text-gray-500">No image</div>
                                )}
                                <div className="text-xs text-gray-600 mt-1 text-center max-w-[5rem] truncate">{match.wardrobe_image_description || match.wardrobe_image_object_name}</div>
                              </div>
                            ))
                          ) : (
                            <div className="text-gray-400">No wardrobe items matched.</div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {recommendationError && (
            <div className="text-center text-red-500 mt-4">{recommendationError}</div>
          )}
        </div>
      </div>
    </>
  )
}
