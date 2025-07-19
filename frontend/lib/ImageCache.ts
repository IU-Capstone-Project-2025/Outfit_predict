// A simple in-memory cache for storing fetched image blobs
const imageCache = new Map<string, string>();

export const getCachedImage = (src: string): string | null => {
  return imageCache.get(src) || null;
};

export const setCachedImage = (src: string, blobUrl: string) => {
  imageCache.set(src, blobUrl);
};
