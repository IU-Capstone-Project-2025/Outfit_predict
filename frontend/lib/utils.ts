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
  return `${getApiBaseUrl()}/api/${path.replace(/^\//, "")}`;
}

// Custom fetch that attaches token and handles 401
export async function fetchWithAuth(input: RequestInfo | URL, init: RequestInit = {}, logoutCallback?: () => void): Promise<Response> {
  let token: string | null = null;
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('token');
  }
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) {
    // Remove token and user info, call logout callback if provided
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user_email');
      localStorage.removeItem('selectedOutfitItems');
    }
    if (logoutCallback) logoutCallback();
    // Optionally, redirect to login if router is available
  }
  return response;
}
