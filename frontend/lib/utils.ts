import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getApiBaseUrl() {
  // Remove trailing slash if present
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
}

// Helper to join API base with a path, avoiding double slashes
export function apiUrl(path: string) {
  return `${getApiBaseUrl()}/${path.replace(/^\//, "")}`;
}
