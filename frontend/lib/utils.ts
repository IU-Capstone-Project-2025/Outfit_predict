import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || 'http://0.0.0.0:8000';
}
