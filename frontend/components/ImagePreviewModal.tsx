import React from "react";

interface ImagePreviewModalProps {
  open: boolean;
  onClose: () => void;
  src: string;
  alt?: string;
  description?: string;
  token?: string | null;
}

function ProtectedImage({ src, alt, token, ...props }: { src: string, alt?: string, token?: string | null } & React.ImgHTMLAttributes<HTMLImageElement>) {
  const [imgUrl, setImgUrl] = React.useState<string | null>(null);

  React.useEffect(() => {
    let isMounted = true;
    if (!src) return;

    // If the image is public or no token is provided, use the src directly
    const isProtectedApi = src.startsWith("/api") || src.includes("/api/");
    if (!isProtectedApi || !token) {
      setImgUrl(src);
      return;
    }

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
      })
      .catch(() => {
        if (isMounted) setImgUrl("/placeholder.svg");
      });

    return () => {
      isMounted = false;
      if (imgUrl) URL.revokeObjectURL(imgUrl);
    };
  }, [src, token]);

  if (!imgUrl) return <div style={{ width: "100%", height: "100%", background: "#222" }} />;

  return <img src={imgUrl} alt={alt} loading="lazy" {...props} />;
}

export { ProtectedImage };

export const ImagePreviewModal: React.FC<ImagePreviewModalProps> = ({ open, onClose, src, alt, description, token }) => {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-3xl p-6 max-w-2xl w-full max-h-[90vh] overflow-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-white">Image Preview</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl bg-gray-800 rounded-full w-8 h-8 flex items-center justify-center">
            ×
          </button>
        </div>
        <ProtectedImage
          src={src}
          alt={alt || "Preview image"}
          token={token}
          className="w-full max-h-96 object-contain rounded-2xl mb-4"
        />
        {description && <p className="text-gray-300 text-center">{description}</p>}
      </div>
    </div>
  );
}; 