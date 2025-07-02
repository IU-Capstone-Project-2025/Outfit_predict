"use client"

import type React from "react"

import { useEffect, useState, useRef, useCallback } from "react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { MoreVertical, Search, Plus, Tag, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { getApiBaseUrl } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"

interface ImageItem {
  id: string
  description: string | null
  object_name: string
  url: string
}

export default function WardrobePage() {
  const [images, setImages] = useState<ImageItem[]>([])
  const [wardrobeLoading, setWardrobeLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImage, setSelectedImage] = useState<ImageItem | null>(null)

  const [searchTerm, setSearchTerm] = useState("")
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [isMessageFadingOut, setIsMessageFadingOut] = useState(false)
  const fadeOutTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const [moreOptionsOpenId, setMoreOptionsOpenId] = useState<string | null>(null)

  const { user, loading } = useAuth()
  const router = useRouter()

  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;

  const showUploadMessage = useCallback((message: string) => {
    if (fadeOutTimeoutRef.current) {
      clearTimeout(fadeOutTimeoutRef.current)
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
      const formData = new FormData()
      formData.append("file", file)
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/v1/images/`, {
          method: "POST",
          body: formData,
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        if (response.ok) {
          showUploadMessage(`Image "${file.name}" uploaded successfully!`)
          const data = await response.json()
          setImages((prev) => [data, ...prev])
        } else {
          showUploadMessage(`Failed to upload "${file.name}".`)
        }
      } catch (error) {
        showUploadMessage(`Error uploading "${file.name}".`)
      }
    },
    [showUploadMessage, token],
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        const selectedFiles = Array.from(e.target.files).filter((file) => file.type === "image/jpeg")
        selectedFiles.forEach(uploadImage)
      }
    },
    [uploadImage],
  )

  const handleDeleteImage = useCallback(async (imageId: string) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/images/${imageId}`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (response.ok) {
        setImages((prev) => prev.filter((img) => img.id !== imageId))
        showUploadMessage("Item deleted successfully!")
      } else {
        showUploadMessage("Failed to delete item.")
      }
    } catch (error) {
      showUploadMessage("Error deleting item.")
    }
    setMoreOptionsOpenId(null)
  }, [showUploadMessage, token])

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login")
      return
    }
  }, [user, loading, router])

  useEffect(() => {
    const fetchImages = async () => {
      setWardrobeLoading(true)
      setError(null)
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/images/`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        if (!res.ok) throw new Error("Failed to fetch images")
        const data = await res.json()
        setImages(data)
      } catch (err: any) {
        setError(err.message || "Unknown error")
      } finally {
        setWardrobeLoading(false)
      }
    }
    fetchImages()
  }, [token])

  const filteredImages = images.filter(
    (img) =>
      img.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      img.object_name.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const LoadingSkeleton = () => (
    <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
      {[...Array(10)].map((_, i) => (
        <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden animate-pulse">
          <div className="aspect-[4/5] bg-gray-200"></div>
          <div className="p-4">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-purple-50/30">
        {/* Main Content */}
        <div className="container mx-auto px-4 py-4">
          {/* Back Button */}
          <div className="mb-2">
            <Link href="/">
              <Button
                variant="ghost"
                className="text-gray-600 hover:text-purple-600 hover:bg-purple-50 p-0 transition-all duration-200 group"
              >
                <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform duration-200" />
                Back to Upload
              </Button>
            </Link>
          </div>

          {/* Page Header with Controls */}
          <div className="flex flex-col items-center justify-center gap-4 mb-10 text-center w-full">
            <h1 className="text-4xl font-bold text-gray-900 bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text">
              My Wardrobe
            </h1>
            <p className="text-gray-600 text-lg">
              {wardrobeLoading
                ? "Loading your collection..."
                : `${filteredImages.length} ${filteredImages.length === 1 ? "item" : "items"} in your collection`}
            </p>
            <div className="flex flex-col sm:flex-row gap-4 w-full max-w-xl items-center justify-center">
              {/* Search */}
              <div className="relative flex-1 w-full max-w-sm">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder="Search your wardrobe..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-12 pr-4 h-12 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent w-full bg-white shadow-sm transition-all duration-200 text-sm hover:shadow-md"
                />
              </div>
              {/* Add Item Button */}
              <div>
                <input
                  type="file"
                  accept="image/jpeg"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="wardrobe-file-upload"
                  multiple
                />
                <label htmlFor="wardrobe-file-upload">
                  <Button
                    className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 px-8 py-3 rounded-2xl cursor-pointer text-sm font-semibold h-12 group"
                    asChild
                  >
                    <span>
                      <Plus className="w-5 h-5 mr-2 group-hover:rotate-90 transition-transform duration-200" />
                      Add Items
                    </span>
                  </Button>
                </label>
              </div>
            </div>
          </div>

          {wardrobeLoading && <LoadingSkeleton />}

          {error && (
            <div className="text-center py-20">
              <div className="bg-white border border-red-200 rounded-3xl p-10 max-w-md mx-auto shadow-lg">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Tag className="w-8 h-8 text-red-500" />
                </div>
                <div className="text-red-600 font-semibold mb-3 text-xl">Error Loading Wardrobe</div>
                <div className="text-red-500 text-sm mb-8">{error}</div>
                <Button
                  onClick={() => window.location.reload()}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-2xl px-6 py-3"
                >
                  Try Again
                </Button>
              </div>
            </div>
          )}

          {!wardrobeLoading && !error && filteredImages.length === 0 && searchTerm && (
            <div className="text-center py-20">
              <div className="bg-white rounded-3xl p-10 max-w-md mx-auto shadow-lg border border-gray-100">
                <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Search className="w-10 h-10 text-gray-400" />
                </div>
                <h3 className="text-2xl font-semibold text-gray-700 mb-3">No items found</h3>
                <p className="text-gray-500 mb-8">Try adjusting your search terms or browse all items</p>
                <Button
                  onClick={() => setSearchTerm("")}
                  variant="outline"
                  className="border-purple-200 text-purple-600 hover:bg-purple-50 rounded-2xl px-6 py-3"
                >
                  Clear Search
                </Button>
              </div>
            </div>
          )}

          {!wardrobeLoading && !error && images.length === 0 && !searchTerm && (
            <div className="text-center py-24">
              <div className="bg-white rounded-3xl p-12 max-w-lg mx-auto shadow-lg border border-gray-100">
                <div className="w-24 h-24 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center mx-auto mb-8">
                  <Tag className="w-12 h-12 text-purple-500" />
                </div>
                <h3 className="text-3xl font-bold text-gray-800 mb-4">Your wardrobe is empty</h3>
                <p className="text-gray-500 mb-10 text-lg leading-relaxed">
                  Start building your collection by uploading photos of your favorite clothes!
                </p>
                <Link href="/">
                  <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-2xl px-10 py-4 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200">
                    Upload Your First Item
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {!wardrobeLoading && !error && filteredImages.length > 0 && (
            <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {filteredImages.map((img) => (
                <div
                  key={img.id}
                  className="bg-white rounded-2xl shadow-md border border-gray-200 hover:shadow-lg cursor-pointer overflow-hidden group"
                  onClick={() => setSelectedImage(img)}
                >
                  {/* Image Container */}
                  <div className="relative aspect-[4/5] overflow-hidden bg-gray-50">
                    <img
                      src={`/api/proxy-image/${img.id}`}
                      alt={img.description || "Clothing item"}
                      className="w-full h-full object-contain"
                    />

                    {/* More Options Button - now opens a menu */}
                    <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="bg-white/95 hover:bg-white text-gray-700 h-10 w-10 rounded-full border border-gray-300 shadow-none relative"
                        onClick={(e) => {
                          e.stopPropagation()
                          setMoreOptionsOpenId(moreOptionsOpenId === img.id ? null : img.id)
                        }}
                      >
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                      {/* Dropdown menu for More Options */}
                      {moreOptionsOpenId === img.id && (
                        <div className="absolute right-0 mt-2 w-36 bg-white border border-gray-200 rounded-xl shadow-lg z-10">
                          <button
                            className="w-full text-left px-4 py-2 text-red-600 hover:bg-red-50 rounded-xl"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteImage(img.id)
                            }}
                          >
                            Delete Item
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Content */}
                  <div className="p-5">
                    <div className="mb-3">
                      <h3 className="text-gray-900 font-semibold text-lg leading-tight line-clamp-2">
                        {img.description || "Untitled Item"}
                      </h3>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500 font-medium bg-gray-100 px-3 py-1 rounded-full">
                        Wardrobe Item
                      </span>
                      <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Simplified Image Modal */}
        {selectedImage && (
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedImage(null)}
          >
            <div
              className="bg-white rounded-3xl p-8 max-w-4xl max-h-[90vh] overflow-auto shadow-2xl border border-gray-200"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-center mb-8">
                <div>
                  <h3 className="text-3xl font-bold text-gray-800">{selectedImage.description || "Untitled Item"}</h3>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedImage(null)}
                  className="text-gray-500 hover:text-gray-700 h-12 w-12 p-0 rounded-full hover:bg-gray-100 transition-all duration-200"
                >
                  ✕
                </Button>
              </div>

              <div className="rounded-2xl overflow-hidden shadow-lg mb-6 bg-gray-50">
                <img
                  src={`/api/proxy-image/${selectedImage.id}`}
                  alt={selectedImage.description || "Clothing item"}
                  className="w-full max-h-96 object-contain"
                />
              </div>

              <div className="flex justify-center">
                <Button
                  onClick={() => setSelectedImage(null)}
                  variant="outline"
                  className="border-gray-300 text-gray-700 hover:bg-gray-50 rounded-xl py-3 px-8"
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Enhanced upload notification */}
        {uploadMessage && (
          <div
            className={`fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-4 rounded-2xl shadow-xl transition-all duration-500 ${
              isMessageFadingOut ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
            } whitespace-nowrap font-semibold`}
          >
            {uploadMessage}
          </div>
        )}
      </div>
    </>
  )
}
