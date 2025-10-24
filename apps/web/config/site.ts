import { Home } from 'lucide-react';
import { Metadata } from 'next';

export const siteConfig: Metadata = {
  title: 'Taboot',
  description: 'Doc-to-Graph RAG platform built on LlamaIndex, Firecrawl, Neo4j, and Qdrant.',
  icons: {
    icon: [{ url: '/favicon.ico' }],
    apple: '/apple-touch-icon.png',
    shortcut: '/favicon.ico',
  },
  keywords: [
    'rag',
    'neo4j',
    'qdrant',
    'llamaindex',
    'firecrawl',
    'knowledge-graph',
    'vector-search',
    'react',
    'typescript',
    'nextjs',
    'tailwindcss',
    'shadcn/ui',
  ],
  openGraph: {
    title: 'Taboot',
    description: 'Doc-to-Graph RAG platform built on LlamaIndex, Firecrawl, Neo4j, and Qdrant.',
    url: process.env.NEXT_PUBLIC_BASE_URL ?? 'http://localhost:3000',
    siteName: 'Taboot',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Taboot',
    description: 'Doc-to-Graph RAG platform built on LlamaIndex, Firecrawl, Neo4j, and Qdrant.',
  },
};

export const config = {
  name: 'Taboot',
  description: siteConfig.description,
  baseUrl: process.env.NEXT_PUBLIC_BASE_URL ?? 'http://localhost:3000',
  domain: process.env.NEXT_PUBLIC_DOMAIN ?? 'localhost',
  nav: [
    {
      title: 'Dashboard',
      href: '/dashboard',
      icon: Home,
    },
  ],
};
