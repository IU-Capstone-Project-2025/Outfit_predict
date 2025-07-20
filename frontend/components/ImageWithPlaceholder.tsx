"use client"

import React from "react"
import { ProtectedImage } from "@/components/ImagePreviewModal"

export function ImageWithPlaceholder({
  src,
  thumbnailSrc,
  alt,
  token,
  className,
  ...props
}: any) {
  const [thumbnailLoaded, setThumbnailLoaded] = React.useState(false)
  return (
    <>
      {!thumbnailLoaded && (
        <img
          src="/placeholder.svg"
          alt="placeholder"
          className={
            className + " absolute inset-0 w-full h-full object-contain z-0"
          }
          style={{ background: "transparent" }}
        />
      )}
      <ProtectedImage
        src={src}
        thumbnailSrc={thumbnailSrc}
        alt={alt}
        token={token}
        className={className + (thumbnailLoaded ? "" : " invisible")}
        onThumbnailLoad={() => setThumbnailLoaded(true)}
        {...props}
      />
    </>
  )
}
