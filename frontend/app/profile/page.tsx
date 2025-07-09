"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { User, Settings, Camera, Trash2, Eye, Shirt } from "lucide-react"
import Link from "next/link"
import { getApiBaseUrl } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"

interface ImageItem {
  id: string
  description: string | null
  object_name?: string
  url: string
}

export default function WardrobePage() {
  const [images, setImages] = useState<ImageItem[]>([])
  const [wardrobeLoading, setWardrobeLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImage, setSelectedImage] = useState<ImageItem | null>(null)

  const { user, loading } = useAuth()
  const router = useRouter()
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;

  // Fetch wardrobe images
  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login")
      return
    }
    const fetchImages = async () => {
      setWardrobeLoading(true)
      setError(null)
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/images/`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        if (!res.ok) throw new Error("Failed to fetch wardrobe images")
        const data = await res.json()
        setImages(data)
      } catch (err: any) {
        setError(err.message || "Unknown error")
        setImages([])
      } finally {
        setWardrobeLoading(false)
      }
    }
    fetchImages()
  }, [user, token, loading, router])

  // Delete image
  const deleteImage = useCallback(async (imageId: string) => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/images/${imageId}`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (res.ok) {
        setImages((prev) => prev.filter((img) => img.id !== imageId))
      }
    } catch (err) {
      // Optionally show error
    }
  }, [token])

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Geometric Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <svg className="w-full h-full" viewBox="0 0 1200 800" fill="none">
          <defs>
            <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
              <path d="M 100 0 L 0 0 0 100" fill="none" stroke="white" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          <path d="M0 0 L400 300 L800 100 L1200 400" stroke="white" strokeWidth="1" fill="none" />
          <path d="M0 800 L300 500 L600 700 L1200 300" stroke="white" strokeWidth="1" fill="none" />
        </svg>
      </div>

      <Header />

      <div className="relative z-10 container mx-auto px-4 py-12">
        {/* Profile Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-full px-6 py-2 mb-8">
            <span className="text-sm text-gray-300">Your Style Profile</span>
          </div>

          <div className="flex items-center justify-center mb-6">
            <div className="w-20 h-20 bg-gray-700 rounded-full flex items-center justify-center mr-6">
              <User className="w-10 h-10 text-gray-300" />
            </div>
            <div className="text-left">
              <h1 className="text-4xl font-bold mb-2">
                Welcome back, <span className="text-gray-400">{user?.email?.split("@")[0] || "User"}</span>
              </h1>
              <p className="text-gray-400 text-lg">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12">
          <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700 rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-white mb-2">{images.length}</div>
            <div className="text-gray-400">Wardrobe Items</div>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700 rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-white mb-2">42</div>
            <div className="text-gray-400">Outfits Generated</div>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700 rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-white mb-2">15</div>
            <div className="text-gray-400">Days Active</div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex justify-center gap-4 mb-12">
          <Link href="/">
            <Button className="bg-white text-black hover:bg-gray-200 rounded-full px-8 py-3 font-semibold transition-all duration-200 flex items-center gap-2">
              <Camera className="w-5 h-5" />
              Upload New Items
            </Button>
          </Link>
          <Button
            variant="outline"
            className="border-gray-600 text-white hover:bg-gray-800 rounded-full px-8 py-3 font-semibold transition-all duration-200 flex items-center gap-2 bg-transparent"
          >
            <Settings className="w-5 h-5" />
            Settings
          </Button>
        </div>

        {/* Wardrobe Section */}
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold flex items-center gap-3">
              <Shirt className="w-8 h-8" />
              My Profile
            </h2>
            <div className="text-gray-400">{images.length} items</div>
          </div>

          {wardrobeLoading ? (
            <div className="text-center py-12">
              <div className="text-xl text-gray-400">Loading your profile...</div>
            </div>
          ) : images.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-xl text-gray-400 mb-4">Your profile is empty</div>
              <Link href="/">
                <Button className="bg-white text-black hover:bg-gray-200 rounded-full px-8 py-3 font-semibold">
                  Add Your First Items
                </Button>
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {images.map((image, index) => (
                <div
                  key={image.id || index}
                  className="group relative bg-gray-900 rounded-2xl overflow-hidden border border-gray-700 hover:border-gray-500 transition-all duration-200 h-72 flex flex-col"
                >
                  <div className="flex-1 flex items-center justify-center bg-black aspect-square h-full">
                    <ProtectedImage
                      src={image.url}
                      alt={image.description || `Wardrobe item ${index + 1}`}
                      token={token}
                      className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                    />
                  </div>

                  {/* Overlay */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-all duration-200 flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSelectedImage(image)}
                        className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white/30 transition-colors"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => deleteImage(image.id)}
                        className="w-10 h-10 bg-red-500/20 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-red-500/30 transition-colors"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  {/* Description */}
                  {image.description && (
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                      <p className="text-white text-sm truncate">{image.description}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Image Preview Modal */}
        {selectedImage && (
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedImage(null)}
          >
            <div
              className="bg-gray-900 border border-gray-700 rounded-3xl p-6 max-w-2xl w-full max-h-[90vh] overflow-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-semibold">Wardrobe Item</h3>
                <button onClick={() => setSelectedImage(null)} className="text-gray-400 hover:text-white text-2xl">
                  ×
                </button>
              </div>
              <ProtectedImage
                src={selectedImage.url}
                alt={selectedImage.description || "Wardrobe item"}
                token={token}
                className="w-full max-h-96 object-contain rounded-2xl mb-4"
              />
              {selectedImage.description && <p className="text-gray-300 text-center">{selectedImage.description}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ProtectedImage({ src, alt, token, ...props }: { src: string, alt: string, token: string | null } & React.ImgHTMLAttributes<HTMLImageElement>) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (!src || !token) return;

    fetch(src, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch image");
        return res.blob();
      })
      .then(blob => {
        if (isMounted) setImgUrl(URL.createObjectURL(blob));
      });

    return () => {
      isMounted = false;
      if (imgUrl) URL.revokeObjectURL(imgUrl);
    };
  }, [src, token]);

  if (!imgUrl) return <div style={{ width: "100%", height: "100%", background: "#222" }} />;

  return <img src={imgUrl} alt={alt} {...props} />;
}
