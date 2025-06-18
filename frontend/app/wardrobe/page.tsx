"use client"

import React, { useEffect, useState } from "react";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";

interface ImageItem {
  id: string;
  description: string;
  object_name: string;
  url: string;
}

export default function WardrobePage() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchImages = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("http://localhost:8000/api/v1/images/");
        if (!res.ok) throw new Error("Failed to fetch images");
        const data = await res.json();
        setImages(data);
      } catch (err: any) {
        setError(err.message || "Unknown error");
      } finally {
        setLoading(false);
      }
    };
    fetchImages();
  }, []);

  return (
    <>
      <Header />
      <main className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 py-12">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl md:text-4xl font-bold text-center mb-8 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            My Wardrobe
          </h1>
          {loading && (
            <div className="text-center text-gray-500 py-12">Loading your wardrobe...</div>
          )}
          {error && (
            <div className="text-center text-red-500 py-12">{error}</div>
          )}
          {!loading && !error && images.length === 0 && (
            <div className="text-center text-gray-400 py-12">No images uploaded yet.</div>
          )}
          {!loading && !error && images.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
              {images.map((img) => (
                <div
                  key={img.id}
                  className="bg-white/70 rounded-xl shadow-md p-4 flex flex-col items-center hover:shadow-lg transition-shadow"
                >
                  <img
                    src={img.url}
                    alt={img.description || "Clothing image"}
                    className="w-full h-48 object-cover rounded-lg mb-3 border border-gray-200"
                  />
                  <div className="text-gray-700 text-center text-sm truncate w-full">
                    {img.description || <span className="italic text-gray-400">No description</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
} 