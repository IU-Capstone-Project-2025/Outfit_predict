"use client"

import React from "react"
import { Sparkles, Heart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ImagePreviewModal, ProtectedImage } from "@/components/ImagePreviewModal"
import { ImageWithPlaceholder } from "@/components/ImageWithPlaceholder"

interface Recommendation {
  outfit: {
    id: string
    url: string
    thumbnail_url?: string
    style?: string
  }
  matchesWithUrls: any[]
}

interface RecommendationsModalProps {
  show: boolean
  recommendations: Recommendation[]
  onClose: () => void
  onSave: (recommendation: Recommendation) => void
  onPreview: (preview: {
    src: string
    alt: string
    thumbnailSrc?: string
    description?: string
  }) => void
  savingOutfits: Set<string>
  savedOutfits: Set<string>
  token: string | null
}

export function RecommendationsModal({
  show,
  recommendations,
  onClose,
  onSave,
  onPreview,
  savingOutfits,
  savedOutfits,
  token,
}: RecommendationsModalProps) {
  const [selectedStyles, setSelectedStyles] = React.useState([
    "formal",
    "streetwear",
    "minimalist",
    "athleisure",
    "other",
  ])

  if (!show || !recommendations) {
    return null
  }

  const filteredRecommendations = recommendations.filter(rec =>
    selectedStyles.includes(rec.outfit?.style || "other")
  )

  return (
    <div
      className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900/95 border border-gray-700/50 rounded-3xl p-10 max-w-6xl w-full max-h-[90vh] overflow-auto shadow-2xl relative"
        onClick={e => e.stopPropagation()}
      >
        <button
          className="absolute top-8 right-8 flex items-center justify-center w-12 h-12 rounded-full text-gray-300 hover:text-white text-3xl font-light transition-colors hover:bg-gray-800/50"
          onClick={onClose}
        >
          ×
        </button>

        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4 text-white">
            Your AI-Generated Outfits
          </h2>
          <p className="text-gray-400 text-lg">
            Here are personalized outfit combinations based on your wardrobe
          </p>
        </div>

        {/* Style Filter Dropdown */}
        <div className="mb-8">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-lg font-medium text-white">
              Filter by Style:
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                "formal",
                "streetwear",
                "minimalist",
                "athleisure",
                "other",
              ].map(style => (
                <button
                  key={style}
                  onClick={() => {
                    setSelectedStyles(prev =>
                      prev.includes(style)
                        ? prev.filter(s => s !== style)
                        : [...prev, style]
                    )
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
                onClick={() =>
                  setSelectedStyles([
                    "formal",
                    "streetwear",
                    "minimalist",
                    "athleisure",
                    "other",
                  ])
                }
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

        {filteredRecommendations.length === 0 ? (
          <div className="text-center text-gray-400 text-xl py-16">
            <div className="w-16 h-16 bg-gray-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-gray-500" />
            </div>
            {recommendations.length === 0
              ? "No outfit recommendations found. Try uploading more clothing items."
              : "No outfits match the selected styles. Try selecting different style filters."}
          </div>
        ) : (
          <div className="space-y-12">
            {filteredRecommendations.map((rec, idx) => (
              <div
                key={rec.outfit.id}
                className="bg-gray-900/80 rounded-3xl p-8 border border-gray-700/50"
              >
                <div className="flex flex-col lg:flex-row gap-10 items-center">
                  {/* For the main outfit image */}
                  <div className="relative w-72 h-72 flex-shrink-0">
                    {/* Placeholder */}
                    <img
                      src="/placeholder.svg"
                      alt="placeholder"
                      className="absolute inset-0 w-full h-full object-contain rounded-3xl z-0"
                    />
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
                      onClick={() =>
                        onPreview({
                          src: rec.outfit.url || "/placeholder.svg",
                          alt: `Generated Outfit #${idx + 1}`,
                          thumbnailSrc: rec.outfit.thumbnail_url,
                        })
                      }
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
                      <span className="text-white text-sm font-medium">
                        Outfit #{idx + 1}
                      </span>
                    </div>
                    <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-full px-3 py-1 z-20">
                      <span className="text-black text-xs font-semibold">
                        {(rec.outfit?.style || "other")
                          .charAt(0)
                          .toUpperCase() +
                          (rec.outfit?.style || "other").slice(1)}
                      </span>
                    </div>
                    {/* Save button */}
                    <div className="absolute bottom-4 right-4 z-20">
                      <Button
                        onClick={e => {
                          e.stopPropagation()
                          onSave(rec)
                        }}
                        disabled={
                          savingOutfits.has(rec.outfit.id) ||
                          savedOutfits.has(rec.outfit.id)
                        }
                        className={`rounded-full p-3 transition-all duration-200 ${
                          savedOutfits.has(rec.outfit.id)
                            ? "bg-black text-white cursor-default"
                            : savingOutfits.has(rec.outfit.id)
                            ? "bg-white/70 text-gray-500 cursor-not-allowed"
                            : "bg-white/90 text-black hover:bg-white hover:scale-110 cursor-pointer"
                        }`}
                        title={
                          savedOutfits.has(rec.outfit.id)
                            ? "Already saved"
                            : "Save outfit"
                        }
                      >
                        {savingOutfits.has(rec.outfit.id) ? (
                          <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                          <Heart
                            className={`w-5 h-5 ${
                              savedOutfits.has(rec.outfit.id)
                                ? "fill-current"
                                : ""
                            }`}
                          />
                        )}
                      </Button>
                    </div>
                  </div>

                  <div className="flex-1">
                    <h3 className="text-2xl font-bold text-white mb-6">
                      Matched Wardrobe Items
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                      {rec.matchesWithUrls && rec.matchesWithUrls.length > 0 ? (
                        rec.matchesWithUrls.map((match: any, i: number) => {
                          const isSuggested = !match.wardrobe_image_object_name
                          const imageUrl = isSuggested
                            ? match.suggested_item_image_link
                            : match.wardrobe_image_url
                          const itemAlt = isSuggested
                            ? "Suggested item"
                            : match.wardrobe_image_description || "Wardrobe item"

                          const imageContainer = (
                            <div
                              className={`absolute inset-0 flex items-center justify-center z-10 ${
                                isSuggested ? "" : "cursor-pointer"
                              }`}
                            >
                              <ImageWithPlaceholder
                                src={imageUrl || "/placeholder.svg"}
                                thumbnailSrc={
                                  isSuggested
                                    ? undefined
                                    : match.wardrobe_image_thumbnail_url
                                }
                                alt={itemAlt}
                                token={isSuggested ? null : token}
                                className="w-full h-full object-contain rounded-2xl"
                              />
                            </div>
                          )

                          return (
                            <div
                              key={match.outfit_item_id || i}
                              className="text-center relative w-32 h-32 mx-auto"
                            >
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
                                  token={isSuggested ? null : token}
                                  className="w-full h-full object-cover scale-110 blur-lg"
                                />
                              </div>

                              {isSuggested ? (
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
                                  className="w-full h-full"
                                  onClick={() =>
                                    onPreview({
                                      src:
                                        match.wardrobe_image_url ||
                                        "/placeholder.svg",
                                      thumbnailSrc:
                                        match.wardrobe_image_thumbnail_url,
                                      alt:
                                        match.wardrobe_image_description ||
                                        "Wardrobe item",
                                      description:
                                        match.wardrobe_image_description,
                                    })
                                  }
                                >
                                  {imageContainer}
                                </div>
                              )}

                              {/* Suggested Item Badge & Styling */}
                              {isSuggested && (
                                <>
                                  <div className="absolute inset-0 rounded-2xl border-2 border-dashed border-yellow-400 z-10 pointer-events-none"></div>
                                  <div className="absolute top-1 right-1 bg-yellow-400/90 text-black text-[10px] font-bold px-2 py-0.5 rounded-full z-20">
                                    SUGGESTED
                                  </div>
                                </>
                              )}

                              <p className="relative z-20 text-sm text-gray-300 font-medium max-w-[8rem] mx-auto truncate mt-2">
                                {isSuggested
                                  ? "Suggested Item"
                                  : match.wardrobe_image_description || ""}
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
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
