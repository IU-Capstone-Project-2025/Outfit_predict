"use client"

import { useEffect, useState } from "react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Heart, ArrowLeft, Trash2, Eye, Download } from "lucide-react"
import Link from "next/link"
import { apiUrl, fetchWithAuth } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { ImagePreviewModal, ProtectedImage } from "@/components/ImagePreviewModal"
import { toPng } from "html-to-image";
import React, { useRef } from "react";

interface MatchedItem {
  wardrobe_image_index: number | null
  wardrobe_image_object_name: string | null
  clothing_type: string | null
  external_image_url: string | null
  suggested_item_product_link: string | null
  outfit_item_id: string
  score: number | null
}

interface SavedOutfit {
  id: string
  user_id: string
  outfit_id: string
  completeness_score: number
  matches: MatchedItem[]
  created_at: string
  outfit: {
    id: string
    url: string
    object_name: string
    created_at: string
  }
}

// Helper component for image with placeholder
function ImageWithPlaceholder({ src, thumbnailSrc, alt, token, className, ...props }: any) {
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false)
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
  )
}

export default function SavedOutfitsPage() {
  const [savedOutfits, setSavedOutfits] = useState<SavedOutfit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [previewImage, setPreviewImage] = useState<{
    src: string
    thumbnailSrc?: string
    alt?: string
    description?: string
  } | null>(null)
  const [wardrobeUrls, setWardrobeUrls] = useState<Record<string, any>>({})

  // Ref array for card elements
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  // Download handler using a cloned node
  const handleDownload = async (idx: number) => {
    const card = cardRefs.current[idx];
    if (!card) return;
    try {
      // Clone the card node
      const clone = card.cloneNode(true) as HTMLElement;

      // Remove unwanted elements from the clone
      clone.querySelectorAll('.saved-label-download-hide').forEach(el => el.remove());
      clone.querySelectorAll('.delete-button-download-hide').forEach(el => el.remove());
      clone.querySelectorAll('.download-button-download-hide').forEach(el => el.remove());

      // Set background color to gray-950 for the clone (for download only)
      clone.style.backgroundColor = '#111827'; // Tailwind gray-900

      // Create a container to hold the clone (offscreen)
      const container = document.createElement('div');
      container.style.position = 'fixed';
      container.style.left = '-9999px';
      container.appendChild(clone);
      document.body.appendChild(container);

      // Export the clone as image
      const dataUrl = await toPng(clone);

      // Clean up
      document.body.removeChild(container);

      // Download
      const link = document.createElement("a");
      link.download = `outfit-${idx + 1}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error("Failed to download image", err);
    }
  };

  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

  // Helper to handle logout and redirect
  const handle401Logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      localStorage.removeItem('user_email')
      localStorage.removeItem('selectedOutfitItems')
    }
    router.replace('/login')
  }

  // Fetch saved outfits
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      router.replace('/login')
      return
    }

    const fetchSavedOutfits = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetchWithAuth(apiUrl('v1/saved-outfits/'), {}, handle401Logout)
        if (!response.ok) throw new Error("Failed to fetch saved outfits")
        const data = await response.json()
        setSavedOutfits(data)

        // Fetch wardrobe image URLs for all matches
        const allObjectNames = new Set<string>()
        data.forEach((outfit: SavedOutfit) => {
          outfit.matches.forEach((match) => {
            if (match.wardrobe_image_object_name) {
              allObjectNames.add(match.wardrobe_image_object_name)
            }
          })
        })

        // Fetch URLs for all unique object names
        const urlPromises = Array.from(allObjectNames).map(async (objectName) => {
          try {
            const urlRes = await fetchWithAuth(
              apiUrl(`v1/utilities/${encodeURIComponent(objectName)}/url`),
              {},
              handle401Logout
            )
            if (urlRes.ok) {
              const urlData = await urlRes.json()
              return { objectName, ...urlData }
            }
          } catch (e) {
            console.warn(`Failed to fetch URL for ${objectName}`)
          }
          return { objectName, url: "/placeholder.svg" }
        })

        const urlResults = await Promise.all(urlPromises)
        const urlMap: Record<string, any> = {}
        urlResults.forEach((result) => {
          if (result) {
            urlMap[result.objectName] = result
          }
        })
        setWardrobeUrls(urlMap)
      } catch (err: any) {
        setError(err.message || "Unknown error")
        setSavedOutfits([])
      } finally {
        setLoading(false)
      }
    }

    fetchSavedOutfits()
  }, [user, authLoading, token, router])

  // Delete saved outfit
  const deleteSavedOutfit = async (savedOutfitId: string) => {
    if (!user) return
    try {
      const response = await fetchWithAuth(
        apiUrl(`v1/saved-outfits/${savedOutfitId}`),
        { method: 'DELETE' },
        handle401Logout
      )
      if (!response.ok) throw new Error("Failed to delete saved outfit")

      // Remove from local state
      setSavedOutfits(prev => prev.filter(outfit => outfit.id !== savedOutfitId))
    } catch (err: any) {
      console.error("Error deleting saved outfit:", err)
      alert("Failed to delete saved outfit. Please try again.")
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden">
        <Header />
        <div className="text-center py-24">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-800/50 rounded-full mb-6">
            <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h3 className="text-2xl font-semibold mb-2">Loading Your Saved Outfits</h3>
          <p className="text-gray-400">Please wait while we fetch your collection...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden">
        <Header />
        <div className="text-center py-24">
          <h3 className="text-2xl font-semibold mb-4">Please Log In</h3>
          <p className="text-gray-400 mb-8">You need to be logged in to view your saved outfits.</p>
          <Link href="/login">
            <Button className="bg-white text-black hover:bg-gray-200 rounded-full px-8 py-3 font-semibold">
              Go to Login
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-[0.03]">
        <svg className="w-full h-full" viewBox="0 0 1200 800" fill="none">
          <defs>
            <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
              <path d="M 80 0 L 0 0 0 80" fill="none" stroke="white" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <Header />

      <ImagePreviewModal
        open={!!previewImage}
        onClose={() => setPreviewImage(null)}
        src={previewImage?.src || ""}
        thumbnailSrc={previewImage?.thumbnailSrc}
        alt={previewImage?.alt}
        description={previewImage?.description}
        token={token}
      />

      <div className="relative z-10 container mx-auto px-4 py-12">
        {/* Page Header */}
        <div className="text-center mb-16">
          <div className="flex items-center justify-center gap-4 mb-8">
            <Link href="/profile">
              <Button className="bg-gray-800/50 text-white hover:bg-gray-700/50 rounded-full p-3 transition-all duration-200">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
                         <div className="inline-flex items-center bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-full px-6 py-2">
               <Heart className="w-5 h-5 text-gray-300 mr-2" />
               <span className="text-sm text-gray-300 font-medium">Your Collection</span>
             </div>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight">
            Saved Outfits
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto leading-relaxed">
            Your curated collection of favorite outfit combinations
          </p>
        </div>

        {/* Stats */}
        <div className="flex justify-center mb-12">
          <div className="bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-3xl p-4 text-center max-w-xs w-full">
            <div className="text-3xl font-bold text-white mb-2">{savedOutfits.length}</div>
            <div className="text-gray-400">Saved Outfits</div>
          </div>
        </div>

        {/* Content */}
        {error ? (
          <div className="text-center py-12">
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 max-w-md mx-auto">
              <h3 className="text-xl font-semibold text-red-400 mb-2">Error Loading Outfits</h3>
              <p className="text-red-300">{error}</p>
            </div>
          </div>
        ) : savedOutfits.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-gray-800/50 rounded-full flex items-center justify-center mx-auto mb-8">
              <Heart className="w-12 h-12 text-gray-500" />
            </div>
            <h3 className="text-2xl font-semibold mb-4">No Saved Outfits Yet</h3>
            <p className="text-gray-400 mb-8 max-w-md mx-auto">
              Start generating outfits and save your favorites by clicking the heart icon on any recommendation.
            </p>
            <Link href="/">
              <Button className="bg-white text-black hover:bg-gray-200 rounded-full px-8 py-3 font-semibold">
                Generate Outfits
              </Button>
            </Link>
          </div>
        ) : (
          <div className="max-w-6xl mx-auto">
            <div className="space-y-12">
              {savedOutfits.map((savedOutfit, idx) => (
                <div
                  key={savedOutfit.id}
                  ref={el => {
                    cardRefs.current[idx] = el;
                  }}
                  className="bg-gray-900/80 rounded-3xl p-8 border border-gray-700/50 relative"
                >
                  <div className="flex flex-col lg:flex-row gap-10 items-start">
                    {/* Outfit Image */}
                    <div className="relative w-72 h-72 flex-shrink-0 mx-auto lg:mx-0">
                      {/* Placeholder */}
                      <img
                        src="/placeholder.svg"
                        alt="placeholder"
                        className="absolute inset-0 w-full h-full object-contain rounded-3xl z-0"
                      />
                      {/* Blurred background */}
                      <div className="absolute inset-0 rounded-3xl overflow-hidden z-0">
                        <ProtectedImage
                          src={savedOutfit.outfit.url || "/placeholder.svg"}
                          alt=""
                          token={token}
                          className="w-full h-full object-cover scale-110 blur-lg"
                        />
                      </div>
                      {/* Main image */}
                      <div
                        className="absolute inset-0 flex items-center justify-center cursor-pointer z-10"
                        onClick={() => setPreviewImage({
                          src: savedOutfit.outfit.url || "/placeholder.svg",
                          alt: `Saved Outfit #${idx + 1}`,
                        })}
                      >
                        <ImageWithPlaceholder
                          src={savedOutfit.outfit.url || "/placeholder.svg"}
                          alt="Saved Outfit"
                          token={token}
                          className="w-full h-full object-contain rounded-3xl"
                        />
                      </div>
                      {/* Labels */}
                      <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-sm rounded-full px-4 py-2 z-20 saved-label-download-hide">
                        <span className="text-white text-sm font-medium flex items-center gap-2">
                          <Heart className="w-4 h-4 fill-current" />
                          Saved
                        </span>
                      </div>
                    </div>

                    {/* Outfit Details */}
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="text-2xl font-bold text-white">Matched Wardrobe Items</h3>
                        <Button
                          onClick={() => deleteSavedOutfit(savedOutfit.id)}
                          className="bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-gray-300 rounded-full p-2 transition-all duration-200 delete-button-download-hide"
                          title="Remove from saved"
                          variant="ghost"
                          size="icon"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>

                      {/* Matches Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-6 mb-6">
                        {savedOutfit.matches && savedOutfit.matches.length > 0 ? (
                          savedOutfit.matches.map((match: MatchedItem, i: number) => {
                            const isWardrobeItem = !!match.wardrobe_image_object_name;
                            const wardrobeUrl = isWardrobeItem ? wardrobeUrls[match.wardrobe_image_object_name as string] : null;
                            const isSuggested = !isWardrobeItem;

                            const imageUrl = isWardrobeItem ? wardrobeUrl?.url : match.external_image_url;
                            const thumbnailUrl = isWardrobeItem ? wardrobeUrl?.thumbnail_url : undefined;
                            const itemAlt = isWardrobeItem ? wardrobeUrl?.description || "Wardrobe item" : match.clothing_type || "Suggested item";
                            const itemDescription = isWardrobeItem ? wardrobeUrl?.description : `Suggested ${match.clothing_type}`;

                            const imageContainer = (
                              <div className="w-full h-full">
                                {/* Placeholder */}
                                <img
                                  src="/placeholder.svg"
                                  alt="placeholder"
                                  className="absolute inset-0 w-full h-full object-contain rounded-2xl z-0"
                                />
                                {/* Blurred background */}
                                <div className="absolute inset-0 rounded-2xl overflow-hidden z-0">
                                  <ProtectedImage
                                    src={imageUrl || "/placeholder.svg"}
                                    alt=""
                                    token={token}
                                    className="w-full h-full object-cover scale-110 blur-lg"
                                  />
                                </div>
                                {/* Main image */}
                                <div className="absolute inset-0 flex items-center justify-center z-10">
                                  <ImageWithPlaceholder
                                    src={imageUrl || "/placeholder.svg"}
                                    thumbnailSrc={thumbnailUrl}
                                    alt={itemAlt}
                                    token={token}
                                    className="w-full h-full object-contain rounded-2xl"
                                  />
                                </div>
                              </div>
                            );

                            return (
                              <div key={match.outfit_item_id || i} className="text-center relative w-32 h-32 mx-auto">
                                {isSuggested && match.suggested_item_product_link ? (
                                  <a
                                    href={match.suggested_item_product_link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block w-full h-full"
                                  >
                                    {imageContainer}
                                  </a>
                                ) : (
                                  <div
                                    className="w-full h-full cursor-pointer"
                                    onClick={() => {
                                      if (isWardrobeItem) {
                                        setPreviewImage({
                                          src: wardrobeUrl?.url || "/placeholder.svg",
                                          thumbnailSrc: wardrobeUrl?.thumbnail_url,
                                          alt: wardrobeUrl?.description || "Wardrobe item",
                                          description: wardrobeUrl?.description
                                        });
                                      }
                                    }}
                                  >
                                    {imageContainer}
                                  </div>
                                )}

                                {/* Suggested Item Badge & Styling */}
                                {isSuggested && (
                                  <>
                                    <div className="absolute inset-0 rounded-2xl border-2 border-dashed border-yellow-400 z-10 pointer-events-none"></div>
                                    <div className="absolute top-1 right-1 bg-yellow-400/90 text-black text-[10px] font-bold px-2 py-0.5 rounded-full z-20 pointer-events-none">
                                      SUGGESTED
                                    </div>
                                  </>
                                )}

                                <p className="pointer-events-none relative z-20 text-sm text-gray-300 font-medium max-w-[8rem] mx-auto truncate mt-2">
                                  {isWardrobeItem ? wardrobeUrl?.description || '' : match.clothing_type || ''}
                                </p>
                              </div>
                            )
                          })
                        ) : (
                          <div className="col-span-full text-center text-gray-400 text-lg py-8">
                            No wardrobe items matched for this outfit.
                          </div>
                        )}
                      </div>

                      {/* Saved date */}
                      <div className="text-sm text-gray-500">
                        Saved on {new Date(savedOutfit.created_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric'
                        })}
                      </div>
                    </div>
                  </div>
                  {/* Download Button at bottom right */}
                  <div className="absolute bottom-6 right-6 download-button-download-hide">
                    <Button
                      onClick={() => handleDownload(idx)}
                      className="bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-gray-300 rounded-full p-2 transition-all duration-200"
                      title="Download as image"
                      variant="ghost"
                      size="icon"
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
