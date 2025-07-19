"use client"

import React, { useState, useCallback, useRef } from "react"
import { Upload, Sparkles, Heart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/header"
import { getApiBaseUrl, apiUrl, fetchWithAuth } from "@/lib/utils"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { ImagePreviewModal, ProtectedImage } from "@/components/ImagePreviewModal";

// Add a helper component for image with placeholder
function ImageWithPlaceholder({ src, thumbnailSrc, alt, token, className, ...props }: any) {
  const [thumbnailLoaded, setThumbnailLoaded] = React.useState(false);
  return (
    <>
      {!thumbnailLoaded && (
        <img
          src="/placeholder.svg"
          alt="placeholder"
          className={className + " absolute inset-0 w-full h-full object-contain z-0"}
          style={{ background: 'transparent' }}
        />
      )}
      <ProtectedImage
        src={src}
        thumbnailSrc={thumbnailSrc}
        alt={alt}
        token={token}
        className={className + (thumbnailLoaded ? '' : ' invisible')}
        onThumbnailLoad={() => setThumbnailLoaded(true)}
        {...props}
      />
    </>
  );
}

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
  const { user, loading } = useAuth()
  const router = useRouter()
  const [previewImage, setPreviewImage] = useState<{
    src: string;
    thumbnailSrc?: string;
    alt?: string;
    description?: string;
  } | null>(null);
  const [selectedStyles, setSelectedStyles] = useState<string[]>([
    "formal", "streetwear", "minimalist", "athleisure", "other"
  ]); // All styles selected by default
  const [savedOutfits, setSavedOutfits] = useState<Set<string>>(new Set())
  const [savingOutfits, setSavingOutfits] = useState<Set<string>>(new Set())

  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;

  // Helper to handle logout and redirect
  const handle401Logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      localStorage.removeItem('user_email')
      localStorage.removeItem('selectedOutfitItems')
    }
    router.replace('/login')
  }

  // Save outfit function
  const saveOutfit = useCallback(async (recommendation: any) => {
    if (!user || !recommendation) return

    const outfitId = recommendation.outfit.id
    setSavingOutfits(prev => new Set(prev).add(outfitId))

    try {
      const saveData = {
        outfit_id: outfitId,
        completeness_score: recommendation.recommendation.completeness_score,
        matches: recommendation.recommendation.matches
      }

      const response = await fetchWithAuth(
        apiUrl('v1/saved-outfits/'),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(saveData)
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
      showUploadMessage(err.message || "Failed to save outfit. Please try again.")
    } finally {
      setSavingOutfits(prev => {
        const newSet = new Set(prev)
        newSet.delete(outfitId)
        return newSet
      })
    }
  }, [user, token, router])

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
    if (!user) {
      return;
    }
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
      } else {
        showUploadMessage(`Failed to upload "${file.name}".`)
      }
    } catch (error) {
      showUploadMessage(`Error uploading "${file.name}".`)
    }
  }, [showUploadMessage, token, user])

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
    if (!user) {
      return;
    }
    setLoadingRecommendations(true)
    setRecommendationError(null)
    try {
      const selectedObjectNames = JSON.parse(localStorage.getItem("selectedOutfitItems") || "[]");

      let requestBody: { object_names?: string[]; image_ids?: string[] } = {};
      let endpoint = 'v1/outfits/search-similar/';

      if (selectedObjectNames.length > 0) {
        requestBody = { object_names: selectedObjectNames };
        endpoint = 'v1/outfits/search-similar-subset/';
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
      const recsWithUrls = await Promise.all(recs.map(async (rec: any) => {
        const matchesSrc = rec.recommendation?.matches || [];
        const matchesWithUrls = await Promise.all(matchesSrc.map(async (match: any) => {
          let wardrobe_image_url = undefined;
          let wardrobe_image_thumbnail_url = undefined;
          let wardrobe_image_description = undefined;
          if (match.wardrobe_image_object_name) {
            try {
              const urlRes = await fetch(apiUrl(`v1/utilities/${encodeURIComponent(match.wardrobe_image_object_name)}/url`), {
                headers: {
                  ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
              });
              if (urlRes.ok) {
                const urlData = await urlRes.json();
                wardrobe_image_url = urlData.url;
                wardrobe_image_thumbnail_url = urlData.thumbnail_url;
                wardrobe_image_description = urlData.description;
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
          };
        }));
        return {
          ...rec,
          matchesWithUrls,
        };
      }));
      setRecommendations(recsWithUrls)
      setShowRecommendations(true)

              // Check which outfits are already saved
        try {
          const savedResponse = await fetchWithAuth(apiUrl('v1/saved-outfits/'), {}, handle401Logout)
          if (savedResponse.ok) {
            const savedData = await savedResponse.json()
            const savedIds = new Set<string>(savedData.map((saved: any) => saved.outfit_id))
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

      {/* Recommendations Modal rendered at the top level, outside main content, to avoid header overlay */}
      {showRecommendations && recommendations && !previewImage && (
        <div
          className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => {
            if (!previewImage) setShowRecommendations(false);
          }}
        >
          <div
            className="bg-gray-900/95 border border-gray-700/50 rounded-3xl p-10 max-w-6xl w-full max-h-[90vh] overflow-auto shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="absolute top-8 right-8 flex items-center justify-center w-12 h-12 rounded-full text-gray-300 hover:text-white text-3xl font-light transition-colors hover:bg-gray-800/50"
              onClick={() => setShowRecommendations(false)}
            >
              ×
            </button>

            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold mb-4 text-white">Your AI-Generated Outfits</h2>
              <p className="text-gray-400 text-lg">Here are personalized outfit combinations based on your wardrobe</p>
            </div>

            {/* Style Filter Dropdown */}
            <div className="mb-8">
              <div className="flex flex-wrap items-center gap-4">
                <span className="text-lg font-medium text-white">Filter by Style:</span>
                <div className="flex flex-wrap gap-2">
                  {["formal", "streetwear", "minimalist", "athleisure", "other"].map((style) => (
                    <button
                      key={style}
                      onClick={() => {
                        setSelectedStyles(prev =>
                          prev.includes(style)
                            ? prev.filter(s => s !== style)
                            : [...prev, style]
                        );
                      }}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                        selectedStyles.includes(style)
                          ? "bg-white text-black shadow-lg"
                          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                      }`}
                    >
                      {style.charAt(0).toUpperCase() + style.slice(1)}
                    </button>
                  ))}
                </div>
                <div className="ml-auto">
                  <button
                    onClick={() => setSelectedStyles(["formal", "streetwear", "minimalist", "athleisure", "other"])}
                    className="text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    Select All
                  </button>
                  <span className="text-gray-500 mx-2">|</span>
                  <button
                    onClick={() => setSelectedStyles([])}
                    className="text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    Clear All
                  </button>
                </div>
              </div>
            </div>

            {(() => {
              const filteredRecommendations = recommendations.filter(rec =>
                selectedStyles.includes(rec.outfit?.style || "other")
              );

              return filteredRecommendations.length === 0 ? (
                <div className="text-center text-gray-400 text-xl py-16">
                  <div className="w-16 h-16 bg-gray-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="w-8 h-8 text-gray-500" />
                  </div>
                  {recommendations.length === 0 ? (
                    "No outfit recommendations found. Try uploading more clothing items."
                  ) : (
                    "No outfits match the selected styles. Try selecting different style filters."
                  )}
                </div>
              ) : (
                <div className="space-y-12">
                  {filteredRecommendations.map((rec, idx) => (
                  <div key={rec.outfit.id} className="bg-gray-900/80 rounded-3xl p-8 border border-gray-700/50">
                    <div className="flex flex-col lg:flex-row gap-10 items-center">
                      {/* For the main outfit image */}
                      <div className="relative w-72 h-72 flex-shrink-0">
                        {/* Placeholder */}
                        <img src="/placeholder.svg" alt="placeholder" className="absolute inset-0 w-full h-full object-contain rounded-3xl z-0" />
                        {/* Blurred background */}
                        <div className="absolute inset-0 rounded-3xl overflow-hidden z-0">
                          <ProtectedImage
                            src={rec.outfit.url || "/placeholder.svg"}
                            alt=""
                            token={token}
                            className="w-full h-full object-cover scale-110 blur-lg"
                          />
                        </div>
                        {/* Main image */}
                        <div
                          className="absolute inset-0 flex items-center justify-center cursor-pointer z-10"
                          onClick={() => setPreviewImage({
                            src: rec.outfit.url || "/placeholder.svg",
                            alt: `Generated Outfit #${idx + 1}`,
                            thumbnailSrc: rec.outfit.thumbnail_url
                          })}
                        >
                          <ImageWithPlaceholder
                            src={rec.outfit.url || "/placeholder.svg"}
                            thumbnailSrc={rec.outfit.thumbnail_url}
                            alt="Generated Outfit"
                            token={token}
                            className="w-full h-full object-contain rounded-3xl"
                          />
                        </div>
                        <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-sm rounded-full px-4 py-2 z-20">
                          <span className="text-white text-sm font-medium">Outfit #{idx + 1}</span>
                        </div>
                        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-full px-3 py-1 z-20">
                          <span className="text-black text-xs font-semibold">
                            {(rec.outfit?.style || "other").charAt(0).toUpperCase() + (rec.outfit?.style || "other").slice(1)}
                          </span>
                        </div>
                        {/* Save button */}
                        <div className="absolute bottom-4 right-4 z-20">
                          <Button
                            onClick={(e) => {
                              e.stopPropagation()
                              saveOutfit(rec)
                            }}
                            disabled={savingOutfits.has(rec.outfit.id) || savedOutfits.has(rec.outfit.id)}
                            className={`rounded-full p-3 transition-all duration-200 ${
                              savedOutfits.has(rec.outfit.id)
                                ? "bg-black text-white cursor-default"
                                : savingOutfits.has(rec.outfit.id)
                                ? "bg-white/70 text-gray-500 cursor-not-allowed"
                                : "bg-white/90 text-black hover:bg-white hover:scale-110 cursor-pointer"
                            }`}
                            title={savedOutfits.has(rec.outfit.id) ? "Already saved" : "Save outfit"}
                          >
                            {savingOutfits.has(rec.outfit.id) ? (
                              <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                            ) : (
                              <Heart className={`w-5 h-5 ${savedOutfits.has(rec.outfit.id) ? 'fill-current' : ''}`} />
                            )}
                          </Button>
                        </div>
                      </div>

                      <div className="flex-1">
                        <h3 className="text-2xl font-bold text-white mb-6">Matched Wardrobe Items</h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                          {rec.matchesWithUrls && rec.matchesWithUrls.length > 0 ? (
                            rec.matchesWithUrls.map((match: any, i: number) => (
                              <div key={match.outfit_item_id || i} className="text-center relative w-32 h-32 mx-auto">
                                {/* Placeholder */}
                                <img src="/placeholder.svg" alt="placeholder" className="absolute inset-0 w-full h-full object-contain rounded-2xl z-0" />
                                {/* Blurred background */}
                                <div className="absolute inset-0 rounded-2xl overflow-hidden z-0">
                                  <ProtectedImage
                                    src={match.wardrobe_image_url || "/placeholder.svg"}
                                    alt=""
                                    token={token}
                                    className="w-full h-full object-cover scale-110 blur-lg"
                                  />
                                </div>
                                {/* Main image */}
                                <div
                                  className="absolute inset-0 flex items-center justify-center cursor-pointer z-10"
                                  onClick={() => setPreviewImage({
                                    src: match.wardrobe_image_url || "/placeholder.svg",
                                    thumbnailSrc: match.wardrobe_image_thumbnail_url,
                                    alt: match.wardrobe_image_description || "Wardrobe item",
                                    description: match.wardrobe_image_description
                                  })}
                                >
                                  <ImageWithPlaceholder
                                    src={match.wardrobe_image_url || "/placeholder.svg"}
                                    thumbnailSrc={match.wardrobe_image_thumbnail_url}
                                    alt={match.wardrobe_image_description || "Wardrobe item"}
                                    token={token}
                                    className="w-full h-full object-contain rounded-2xl"
                                  />
                                </div>
                                <p className="relative z-20 text-sm text-gray-300 font-medium max-w-[8rem] mx-auto truncate mt-2">
                                  {match.wardrobe_image_description || ''}
                                </p>
                              </div>
                            ))
                          ) : (
                            <div className="col-span-full text-center text-gray-400 text-lg py-8">
                              No wardrobe items matched for this outfit.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  ))}
                </div>
              );
            })()}
          </div>
        </div>
      )}

      <div className="relative z-10 container mx-auto px-4 py-12">
        {!user ? (
          <div className="text-center text-xl text-gray-300 py-24">
            You need to log in to upload images and generate outfits.
            <div className="mt-8 flex justify-center gap-4">
              <a href="/login" className="text-gray-300 hover:text-white transition-colors font-medium px-8 py-3 rounded-full">Login</a>
              <a href="/signup" className="bg-white text-black hover:bg-gray-100 rounded-full px-8 py-3 text-lg font-semibold transition-all duration-200 shadow-lg hover:shadow-xl">Sign Up</a>
            </div>
          </div>
        ) : (
          <>
            {/* Page Header */}
            <div className="text-center mb-16">
              <div className="inline-flex items-center bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-full px-6 py-2 mb-8">
                <span className="text-sm text-gray-300 font-medium">AI-Powered Style Generator</span>
              </div>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight">
                Generate Your Perfect
                <br/>
                Outfit Combinations
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
                    disabled={!user}
                  />

                  <label htmlFor="file-upload">
                    <Button
                      variant="outline"
                      className="cursor-pointer rounded-full border-2 border-gray-500 bg-transparent text-white hover:bg-white hover:text-black transition-all duration-300 px-12 py-5 text-lg font-semibold shadow-lg hover:shadow-xl"
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
          </>
        )}
      </div>
    </div>
  )
}
