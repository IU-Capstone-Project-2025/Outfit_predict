import React from "react";
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { getCachedImage, setCachedImage } from "@/lib/ImageCache";

interface ImagePreviewModalProps {
  open: boolean;
  onClose: () => void;
  src: string;
  thumbnailSrc?: string;
  alt?: string;
  description?: string;
  token?: string | null;
}

interface ProtectedImageProps {
  src: string;
  thumbnailSrc?: string;
  alt?: string;
  token?: string | null;
  loadFullSize?: boolean;
  onThumbnailLoad?: () => void;
  onFullSizeLoad?: () => void;
  className?: string;
  style?: React.CSSProperties;
  [key: string]: any;
}

function ProtectedImage({
  src,
  thumbnailSrc,
  alt,
  token,
  loadFullSize = false,
  onThumbnailLoad,
  onFullSizeLoad,
  ...props
}: ProtectedImageProps) {
  const [thumbnailUrl, setThumbnailUrl] = React.useState<string | null>(null);
  const [fullSizeUrl, setFullSizeUrl] = React.useState<string | null>(null);
  const [thumbnailLoaded, setThumbnailLoaded] = React.useState(false);
  const [fullSizeLoaded, setFullSizeLoaded] = React.useState(false);
  const [currentDisplay, setCurrentDisplay] = React.useState<'loading' | 'thumbnail' | 'fullsize'>('loading');

  // Load thumbnail
  React.useEffect(() => {
    let isMounted = true;
    const thumbnailToLoad = thumbnailSrc || src;

    if (!thumbnailToLoad) return;

    // Check cache first
    const cachedUrl = getCachedImage(thumbnailToLoad);
    if (cachedUrl) {
      setThumbnailUrl(cachedUrl);
      setThumbnailLoaded(true);
      setCurrentDisplay('thumbnail');
      onThumbnailLoad?.();
      return;
    }

    // If the image is public or no token is provided, use the src directly
    const isProtectedApi = thumbnailToLoad.startsWith("/api") || thumbnailToLoad.includes("/api/");
    if (!isProtectedApi || !token) {
      setThumbnailUrl(thumbnailToLoad);
      setThumbnailLoaded(true);
      setCurrentDisplay('thumbnail');
      onThumbnailLoad?.();
      return;
    }

    fetch(thumbnailToLoad, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch thumbnail");
        return res.blob();
      })
      .then(blob => {
        if (isMounted) {
          const blobUrl = URL.createObjectURL(blob);
          setCachedImage(thumbnailToLoad, blobUrl);
          setThumbnailUrl(blobUrl);
          setThumbnailLoaded(true);
          setCurrentDisplay('thumbnail');
          onThumbnailLoad?.();
        }
      })
      .catch(() => {
        if (isMounted) {
          setThumbnailUrl("/placeholder.svg");
          setThumbnailLoaded(true);
          setCurrentDisplay('thumbnail');
        }
      });

    return () => {
      isMounted = false;
    };
  }, [thumbnailSrc, src, token, onThumbnailLoad]);

  // Load full-size image when requested
  React.useEffect(() => {
    let isMounted = true;

    if (!loadFullSize || !src || !thumbnailLoaded) return;

    // If thumbnail and full-size are the same, don't reload
    if (src === thumbnailSrc || src === (thumbnailSrc || src)) {
      setFullSizeLoaded(true);
      setCurrentDisplay('fullsize');
      onFullSizeLoad?.();
      return;
    }

    // Check cache first
    const cachedUrl = getCachedImage(src);
    if (cachedUrl) {
      setFullSizeUrl(cachedUrl);
      setFullSizeLoaded(true);
      setCurrentDisplay('fullsize');
      onFullSizeLoad?.();
      return;
    }

    // If the image is public or no token is provided, use the src directly
    const isProtectedApi = src.startsWith("/api") || src.includes("/api/");
    if (!isProtectedApi || !token) {
      setFullSizeUrl(src);
      setFullSizeLoaded(true);
      setCurrentDisplay('fullsize');
      onFullSizeLoad?.();
      return;
    }

    fetch(src, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch full-size image");
        return res.blob();
      })
      .then(blob => {
        if (isMounted) {
          const blobUrl = URL.createObjectURL(blob);
          setCachedImage(src, blobUrl);
          setFullSizeUrl(blobUrl);
          setFullSizeLoaded(true);
          setCurrentDisplay('fullsize');
          onFullSizeLoad?.();
        }
      })
      .catch(() => {
        // Keep showing thumbnail if full-size fails
        if (isMounted) {
          setCurrentDisplay('thumbnail');
        }
      });

    return () => {
      isMounted = false;
    };
  }, [loadFullSize, src, thumbnailSrc, token, thumbnailLoaded, onFullSizeLoad]);

  // Show loading placeholder if nothing is loaded yet
  if (currentDisplay === 'loading') {
    return <div style={{ width: "100%", height: "100%", background: "#222" }} />;
  }

  // Show thumbnail or full-size based on what's available and current display state
  const imageToShow = currentDisplay === 'fullsize' && fullSizeUrl ? fullSizeUrl : thumbnailUrl;
  const isShowingFullSize = currentDisplay === 'fullsize' && fullSizeUrl;

  if (!imageToShow) {
    return <div style={{ width: "100%", height: "100%", background: "#222" }} />;
  }

  return (
    <img
      src={imageToShow}
      alt={alt}
      loading="lazy"
      {...props}
      style={{
        ...props.style,
        opacity: isShowingFullSize ? 1 : 0.95, // Slight opacity difference to show it's a thumbnail
        transition: 'opacity 0.3s ease'
      }}
    />
  );
}

export const ImagePreviewModal: React.FC<ImagePreviewModalProps> = ({
  open,
  onClose,
  src,
  thumbnailSrc,
  alt,
  description,
  token
}) => {
  const [loadFullSize, setLoadFullSize] = React.useState(false);

  // Load full-size image when modal opens
  React.useEffect(() => {
    if (open) {
      setLoadFullSize(true);
    } else {
      setLoadFullSize(false);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-3xl p-6 max-w-5xl w-full max-h-[95vh] overflow-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-white">Image Preview</h3>
          <button onClick={onClose} className="flex items-center justify-center w-8 h-8 rounded-full text-gray-400 hover:text-white text-2xl bg-gray-800 transition-colors">
            ×
          </button>
        </div>
        <div className="w-full flex items-center justify-center" style={{ minHeight: '16rem', maxHeight: '80vh' }}>
          <TransformWrapper
            doubleClick={{ mode: 'zoomIn' }}
            pinch={{ disabled: false }}
            wheel={{ step: 40 }}
            panning={{ velocityDisabled: true }}
            minScale={1}
            initialScale={1}
          >
            <TransformComponent wrapperClass="w-full h-full flex items-center justify-center">
              <ProtectedImage
                src={src}
                thumbnailSrc={thumbnailSrc}
                alt={alt || "Preview image"}
                token={token}
                loadFullSize={loadFullSize}
                className="w-full max-h-[80vh] object-contain mb-4 select-none"
                draggable={false}
                style={{ touchAction: 'none', userSelect: 'none' }}
              />
            </TransformComponent>
          </TransformWrapper>
        </div>
        {description && <p className="text-gray-300 text-center mt-2">{description}</p>}
      </div>
    </div>
  );
};

// Export both components
export { ProtectedImage };
