"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Trash2, Eye, Search, Grid3X3, List, Plus, Tag, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { getApiBaseUrl } from "@/lib/utils"

interface ImageItem {
  id: string
  description: string | null
  object_name: string
  url: string
}

export default function WardrobePage() {
  const [images, setImages] = useState<ImageItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImage, setSelectedImage] = useState<ImageItem | null>(null)
  const [deletingId] = useState<string | null>(null) // Deletion not supported

  const [searchTerm, setSearchTerm] = useState("")
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [isMessageFadingOut, setIsMessageFadingOut] = useState(false)
  const fadeOutTimeoutRef = useRef<NodeJS.Timeout | null>(null)

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

  const uploadImage = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/images/`, {
        method: "POST",
        body: formData,
      })
      if (response.ok) {
        showUploadMessage(`Image "${file.name}" uploaded successfully!`)
        // Optionally, refresh images after upload
        const data = await response.json()
        setImages((prev) => [data, ...prev])
      } else {
        showUploadMessage(`Failed to upload "${file.name}".`)
      }
    } catch (error) {
      showUploadMessage(`Error uploading "${file.name}".`)
    }
  }, [showUploadMessage])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter((file) => file.type === "image/jpeg")
      selectedFiles.forEach(uploadImage)
    }
  }, [uploadImage])

  useEffect(() => {
    const fetchImages = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/images/`)
        if (!res.ok) throw new Error("Failed to fetch images")
        const data = await res.json()
        setImages(data)
      } catch (err: any) {
        setError(err.message || "Unknown error")
      } finally {
        setLoading(false)
      }
    }
    fetchImages()
  }, [])

  // Deletion is not supported yet
  const handleDelete = async (_imageId: string) => {}

  const filteredImages = images.filter(
    (img) =>
      img.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      img.object_name.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const LoadingSkeleton = () => (
    <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {[...Array(8)].map((_, i) => (
        <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 animate-pulse">
          <div className={`bg-gray-200 rounded-lg mb-4 w-full h-52`}></div>
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </div>
      ))}
    </div>
  )

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        {/* Main Content */}
        <div className="container mx-auto px-4 py-8">
          {/* Back Button */}
          <div className="mb-4">
            <Link href="/">
              <Button
                variant="ghost"
                className="text-gray-600 hover:text-purple-600 hover:bg-purple-50 p-0 transition-all duration-200"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Upload
              </Button>
            </Link>
          </div>

          {/* Page Header with Controls */}
          <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">My Wardrobe</h1>
              <p className="text-gray-600">
                {loading
                  ? "Loading your collection..."
                  : `${filteredImages.length} ${filteredImages.length === 1 ? "item" : "items"} in your collection`}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 w-full lg:w-auto">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search your wardrobe..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent w-full sm:w-72 bg-white shadow-sm transition-all duration-200"
                />
              </div>

              {/* Add Item Button with file input */}
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
                  <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-pink-600 hover:to-purple-600 text-white shadow-lg hover:shadow-xl transition-all duration-200 px-6 py-3 rounded-xl cursor-pointer" asChild>
                    <span><Plus className="w-4 h-4 mr-2" />Add Items</span>
                  </Button>
                </label>
              </div>
            </div>
          </div>

          {loading && <LoadingSkeleton />}

          {error && (
            <div className="text-center py-16">
              <div className="bg-white border border-red-200 rounded-xl p-8 max-w-md mx-auto shadow-sm">
                <div className="text-red-600 font-semibold mb-3 text-lg">Error Loading Wardrobe</div>
                <div className="text-red-500 text-sm mb-6">{error}</div>
                <Button
                  onClick={() => window.location.reload()}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-pink-600 hover:to-purple-600 text-white rounded-xl"
                >
                  Try Again
                </Button>
              </div>
            </div>
          )}

          {!loading && !error && filteredImages.length === 0 && searchTerm && (
            <div className="text-center py-16">
              <div className="bg-white rounded-xl p-8 max-w-md mx-auto shadow-sm border border-gray-100">
                <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-600 mb-2">No items found</h3>
                <p className="text-gray-500">Try adjusting your search terms or browse all items</p>
                <Button
                  onClick={() => setSearchTerm("")}
                  variant="outline"
                  className="mt-4 border-purple-200 text-purple-600 hover:bg-purple-50"
                >
                  Clear Search
                </Button>
              </div>
            </div>
          )}

          {!loading && !error && images.length === 0 && !searchTerm && (
            <div className="text-center py-20">
              <div className="bg-white rounded-xl p-10 max-w-lg mx-auto shadow-sm border border-gray-100">
                <Tag className="w-20 h-20 text-gray-300 mx-auto mb-6" />
                <h3 className="text-2xl font-semibold text-gray-700 mb-3">Your wardrobe is empty</h3>
                <p className="text-gray-500 mb-8 text-lg">
                  Start building your collection by uploading photos of your favorite clothes!
                </p>
                <Link href="/">
                  <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-pink-600 hover:to-purple-600 text-white rounded-xl px-8 py-3 text-lg">
                    Upload Your First Item
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {!loading && !error && filteredImages.length > 0 && (
            <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredImages.map((img) => (
                <div
                  key={img.id}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-lg hover:border-gray-200 transition-all duration-300 group p-5"
                >
                  <div className="relative w-full">
                    <img
                      src={img.url || "/placeholder.svg"}
                      alt={img.description || "Clothing item"}
                      className="object-cover rounded-lg border border-gray-50 w-full h-52"
                    />
                    {/* Overlay buttons */}
                    <div className="absolute inset-0 bg-black/60 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center justify-center gap-3">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="bg-white/95 hover:bg-white text-gray-800 p-0 shadow-lg h-9 w-9 rounded-full"
                        onClick={() => setSelectedImage(img)}
                      >
                        <Eye className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        className="bg-red-500/40 text-white p-0 shadow-lg cursor-not-allowed h-9 w-9 rounded-full"
                        disabled
                        title="Delete is not available yet"
                        onClick={() => {}}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-4">
                    <div className="text-gray-900 font-medium">
                      {img.description || <span className="italic text-gray-400">Untitled Item</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Image Modal */}
        {selectedImage && (
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedImage(null)}
          >
            <div
              className="bg-white rounded-2xl p-8 max-w-3xl max-h-[90vh] overflow-auto shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-2xl font-semibold text-gray-800">{selectedImage.description || "Untitled Item"}</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedImage(null)}
                  className="text-gray-500 hover:text-gray-700 h-10 w-10 p-0 rounded-full hover:bg-gray-100"
                >
                  ✕
                </Button>
              </div>
              <img
                src={selectedImage.url || "/placeholder.svg"}
                alt={selectedImage.description || "Clothing item"}
                className="w-full max-h-96 object-contain rounded-xl"
              />
            </div>
          </div>
        )}

        {/* Global upload notification at bottom center */}
        {uploadMessage && (
          <div
            className={`fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 bg-green-500 text-white px-4 py-2 rounded-xl shadow-lg transition-opacity duration-500 ${isMessageFadingOut ? 'opacity-0' : 'opacity-100'} whitespace-nowrap`}
          >
            {uploadMessage}
          </div>
        )}
      </div>
    </>
  )
} 