"use client";

import { useId } from "react";

interface LogoProps {
  className?: string;
  
  variant?: "full" | "text";
}

export function Logo({ className = "h-6 w-auto", variant = "full" }: LogoProps) {
  const uid = useId().replace(/:/g, "");
  const silverId = `ls-${uid}`;
  const violetId = `lv-${uid}`;
  const gemId = `lg-${uid}`;

  if (variant === "text") {
    return (
      <svg
        viewBox="0 0 240 18"
        className={className}
        aria-label="Obsidian WebDev"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id={silverId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="55%" stopColor="#e2e8f0" />
            <stop offset="100%" stopColor="#94a3b8" />
          </linearGradient>
          <linearGradient id={violetId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ddd6fe" />
            <stop offset="45%" stopColor="#a78bfa" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
        <text
          x="0"
          y="14"
          fontFamily="Arial Black, 'Arial Bold', Impact, sans-serif"
          fontSize="14"
          fontWeight="900"
          letterSpacing="0.5"
          fill={`url(#${silverId})`}
        >
          OBSIDIAN
        </text>
        <text
          x="112"
          y="14"
          fontFamily="Arial Black, 'Arial Bold', Impact, sans-serif"
          fontSize="14"
          fontWeight="900"
          letterSpacing="0.5"
          fill={`url(#${violetId})`}
        >
          WEBDEV
        </text>
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 260 24"
      className={className}
      aria-label="Obsidian WebDev"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id={silverId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="55%" stopColor="#e2e8f0" />
          <stop offset="100%" stopColor="#94a3b8" />
        </linearGradient>
        <linearGradient id={violetId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ddd6fe" />
          <stop offset="45%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id={gemId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#c4b5fd" />
          <stop offset="50%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#6d28d9" />
        </linearGradient>
      </defs>

      
      <polygon
        points="8,0 16,4 16,16 8,24 0,16 0,4"
        fill={`url(#${gemId})`}
        opacity="0.9"
      />
      <polygon
        points="8,0 16,4 8,8 0,4"
        fill="rgba(255,255,255,0.25)"
      />

      
      <text
        x="22"
        y="18"
        fontFamily="Arial Black, 'Arial Bold', Impact, sans-serif"
        fontSize="18"
        fontWeight="900"
        letterSpacing="0.8"
        fill={`url(#${silverId})`}
      >
        OBSIDIAN
      </text>

      
      <text
        x="142"
        y="18"
        fontFamily="Arial Black, 'Arial Bold', Impact, sans-serif"
        fontSize="18"
        fontWeight="900"
        letterSpacing="0.8"
        fill={`url(#${violetId})`}
      >
        WEBDEV
      </text>
    </svg>
  );
}
