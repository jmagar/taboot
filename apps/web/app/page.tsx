'use client';

import Logo from '@/components/logo';
import { Button } from '@taboot/ui/components/button';
import Link from 'next/link';

export default function Page() {
  return (
    <main className="m-auto flex items-center justify-center px-4">
      <div className="bg-background/70 flex max-w-2xl flex-col items-center gap-5 rounded-xl p-8 text-center backdrop-blur">
        <Logo variant="default" />
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Taboot</h1>
        <span className="bg-muted text-muted-foreground rounded px-2 py-1 text-xs font-medium">
          RAG Platform • Knowledge Graph • Vector Search • LlamaIndex
        </span>
        <p className="text-muted-foreground max-w-md">
          Doc-to-Graph RAG platform built on LlamaIndex, Firecrawl, Neo4j, and Qdrant.
          Ingests from 11+ sources, converts docs into knowledge graphs, and provides hybrid retrieval with strict source attribution.
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <Button asChild size="sm">
            <Link href="/dashboard">
              Dashboard
            </Link>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <Link href="https://github.com/jmagar/taboot" target="_blank">
              View on GitHub
            </Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
