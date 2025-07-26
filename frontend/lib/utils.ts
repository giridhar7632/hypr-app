import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const formatMillionsToReadable = (value: number): string => 
    value >= 1000 ? `${(value / 1000000).toFixed(2)} Trillion` : `${value.toFixed(2)} Million`;

export const fetchData = async (url: string) => {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch stocks data');
    }
    return response.json();
  };

export function slideInOut() {
  document.documentElement.animate([
      {
          opacity: 1,  transform: 'translateY(0)'
      },
      {
          opacity: 0.2, transform: 'translateY(-35%)'
      }
  ], {
      duration: 1500,
      easing: 'cubic-bezier(0.87, 0, 0.13, 1)',
      fill: 'forwards',
      pseudoElement: "::view-transition-old(root)"
  })
  document.documentElement.animate([
      {
          clipPath: 'polygon(0% 100%, 100% 100%, 100% 100%, 0% 100%)'
      },
      {
          clipPath: 'polygon(0% 100%, 100% 100%, 100% 0%, 0% 0%)'
      }
  ], {
      duration: 1500,
      easing: 'cubic-bezier(0.87, 0, 0.13, 1)',
      fill: 'forwards',
      pseudoElement: "::view-transition-new(root)"
  })
}