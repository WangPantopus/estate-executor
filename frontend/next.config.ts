import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ── Output & Compression ──────────────────────────────────────────────
  // Standalone output for optimized Docker deployments
  output: "standalone",
  compress: true,

  // ── Image Optimization ────────────────────────────────────────────────
  images: {
    // Allow document thumbnails and avatar images from our storage
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.googleapis.com",
      },
      {
        protocol: "https",
        hostname: "**.amazonaws.com",
      },
    ],
    // Generate optimized formats
    formats: ["image/avif", "image/webp"],
    // Cache optimized images for 1 hour, revalidate daily
    minimumCacheTTL: 3600,
    // Responsive sizes for document thumbnails and avatars
    deviceSizes: [640, 750, 828, 1080, 1200],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
  },

  // ── Headers for CDN & Browser Caching ─────────────────────────────────
  async headers() {
    return [
      {
        // Static assets: long cache with immutable (hashed filenames)
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        // Fonts: long cache
        source: "/fonts/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        // Images: cache for 1 day, allow CDN caching
        source: "/images/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400",
          },
        ],
      },
      {
        // API routes: no caching
        source: "/api/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, no-cache, must-revalidate",
          },
        ],
      },
      {
        // Security headers for all routes
        source: "/:path*",
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },

  // ── Experimental Performance Features ─────────────────────────────────
  experimental: {
    // Optimize package imports — tree-shake large icon/component libraries
    optimizePackageImports: [
      "lucide-react",
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-select",
      "@radix-ui/react-tabs",
      "@radix-ui/react-tooltip",
    ],
  },

  // ── Bundle Analyzer (enable via ANALYZE=true) ─────────────────────────
  ...(process.env.ANALYZE === "true"
    ? {
        webpack(config) {
          // Dynamic import to avoid requiring the package in production
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const { BundleAnalyzerPlugin } = require("webpack-bundle-analyzer");
          config.plugins.push(
            new BundleAnalyzerPlugin({
              analyzerMode: "static",
              reportFilename: "../analyze/client.html",
              openAnalyzer: false,
            }),
          );
          return config;
        },
      }
    : {}),
};

export default nextConfig;
