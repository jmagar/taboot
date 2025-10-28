# Taboot: NotebookLM Clone Specification

**Vision:** Build a shadcn/ui-based NotebookLM clone with feature parity using LlamaIndex, maintaining Taboot's doc-to-graph architecture.

**Status:** Planning Phase
**Target:** Transform `apps/web` into notebook-centric RAG interface

---

## Core Concept Mapping

### NotebookLM → Taboot

| NotebookLM Concept | Taboot Implementation |
|-------------------|----------------------|
| **Notebook** | Project/Session (Neo4j namespace, isolated graph) |
| **Sources** | Ingestion targets (Firecrawl, files, GitHub, etc.) |
| **Chat** | LlamaIndex query engine with graph context |
| **Studio** | Document generation (summaries, guides, FAQs) |
| **Audio Overview** | TTS pipeline (future - not MVP) |

---

## Feature Breakdown

### 1. Notebook Management (MVP)

**UI:** Dashboard with notebook grid/list view

**Data Model:**

```typescript
interface Notebook {
  id: string;
  name: string;
  description?: string;
  createdAt: Date;
  updatedAt: Date;
  sourceCount: number;
  chatCount: number;
  owner: User;
}
```

**Backend:**
- `POST /api/notebooks` - Create notebook
- `GET /api/notebooks` - List user's notebooks
- `GET /api/notebooks/:id` - Get notebook details
- `PATCH /api/notebooks/:id` - Update name/description
- `DELETE /api/notebooks/:id` - Delete notebook + sources + chats

**Neo4j:**

```cypher
// Notebook node with namespace property
CREATE (n:Notebook {
  id: $id,
  name: $name,
  namespace: $namespace,
  createdAt: datetime()
})
```

**UI Components:**
- `NotebookCard` - Thumbnail with metadata
- `NotebookList` - Table view
- `CreateNotebookDialog` - Name + description form
- `NotebookSettingsDialog` - Edit metadata, danger zone

---

### 2. Source Management (MVP)

**UI:** Three-panel layout - Sources (left), Chat (center), Studio (right)

**Supported Source Types:**

| Type | Upload Method | Backend Package | Status |
|------|--------------|-----------------|--------|
| **PDF** | File upload | `packages/ingest` + PyMuPDF | ✅ Ready |
| **Text/Markdown** | File upload or paste | `packages/ingest` | ✅ Ready |
| **Google Docs** | URL | `llama-index-readers-google` | 🔨 TODO |
| **Web pages** | URL | Firecrawl | ✅ Ready |
| **YouTube** | URL | `packages/ingest` YouTube reader | ✅ Ready |
| **GitHub** | Repo URL | `packages/ingest` GitHub reader | ✅ Ready |
| **Audio** | File upload | Whisper transcription | 🔨 TODO |

**Data Model:**

```typescript
interface Source {
  id: string;
  notebookId: string;
  type: 'pdf' | 'text' | 'web' | 'youtube' | 'github' | 'audio';
  name: string;
  url?: string;
  fileSize?: number;
  wordCount: number;
  status: 'uploading' | 'processing' | 'ready' | 'failed';
  error?: string;
  uploadedAt: Date;
  processedAt?: Date;
}
```

**Backend Endpoints:**
- `POST /api/notebooks/:id/sources/upload` - File upload (multipart)
- `POST /api/notebooks/:id/sources/url` - URL ingestion
- `POST /api/notebooks/:id/sources/paste` - Text paste
- `GET /api/notebooks/:id/sources` - List sources
- `DELETE /api/notebooks/:id/sources/:sourceId` - Delete source
- `GET /api/notebooks/:id/sources/:sourceId/status` - Polling endpoint

**Processing Pipeline:**
1. Upload/URL received → Create `Source` record (status: uploading)
2. Dispatch to ingestion worker (Redis queue)
3. Worker: `packages/ingest` → Normalizer → Chunker → Embeddings
4. Worker: Qdrant upsert (namespace: `notebook_{id}`)
5. Worker: Extraction pipeline (async, decoupled)
6. Worker: Neo4j graph writes (namespace: `notebook_{id}`)
7. Update `Source` status: ready

**UI Components:**
- `SourcePanel` - Left panel with source list
- `SourceCard` - Title, type icon, word count, status badge
- `AddSourceDialog` - Tab UI (Upload, URL, Paste, Google Drive)
- `SourceUploadZone` - Drag-drop file zone
- `SourceProcessingIndicator` - Progress spinner + status
- `SourceMenu` - Dropdown (View, Delete)

**Limits (Free Tier):**
- 50 sources per notebook
- 500K words per source
- 200MB file size max

---

### 3. Chat Interface (MVP)

**UI:** Center panel - conversation view with source citations

**Data Model:**

```typescript
interface Chat {
  id: string;
  notebookId: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceCitation[];
  timestamp: Date;
}

interface SourceCitation {
  sourceId: string;
  sourceName: string;
  snippet: string;
  relevanceScore: number;
}
```

**Backend:**
- `POST /api/notebooks/:id/chat` - Send message, stream response
- `GET /api/notebooks/:id/chat/history` - Load conversation

**Query Pipeline (LlamaIndex):**
1. User query → TEI embedding
2. Qdrant vector search (namespace filter: `notebook_{id}`, top-k: 20)
3. Rerank with Qwen3-Reranker (top-k: 5)
4. Neo4j graph traversal (2-hop context from retrieved chunks)
5. Construct prompt with context + citations
6. Qwen3-4B-Instruct generation (streaming)
7. Post-process: Extract source citations, format response

**LlamaIndex Integration:**

```python
# packages/retrieval/query_engines/notebook_engine.py
from llama_index.core import VectorStoreIndex, PropertyGraphIndex
from llama_index.retrievers import HybridRetriever

class NotebookQueryEngine:
    def __init__(self, notebook_id: str):
        self.namespace = f"notebook_{notebook_id}"

        # Vector retrieval
        self.vector_index = VectorStoreIndex.from_vector_store(
            qdrant_store,
            namespace=self.namespace
        )

        # Graph retrieval
        self.graph_index = PropertyGraphIndex.from_existing(
            neo4j_graph,
            namespace=self.namespace
        )

        # Hybrid retriever
        self.retriever = HybridRetriever(
            vector_retriever=self.vector_index.as_retriever(top_k=20),
            graph_retriever=self.graph_index.as_retriever(include_path=True),
            reranker=self.reranker
        )

    async def query(self, query: str) -> QueryResponse:
        # Retrieve context
        nodes = await self.retriever.aretrieve(query)

        # Build prompt with citations
        context = self._build_context(nodes)

        # Generate response (streaming)
        response = await self.llm.astream_chat(
            messages=[
                SystemMessage(content=NOTEBOOK_SYSTEM_PROMPT),
                UserMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
            ]
        )

        # Extract citations
        citations = self._extract_citations(nodes)

        return QueryResponse(text=response, citations=citations)
```

**UI Components:**
- `ChatPanel` - Center panel container
- `ChatMessageList` - Scrollable message history
- `ChatMessage` - User/assistant bubble with citations
- `SourceCitationBadge` - Clickable badge → highlights source in left panel
- `ChatInput` - Textarea with submit button
- `SuggestedQuestions` - Empty state with starter questions
- `StreamingIndicator` - Typing animation during response

**Features:**
- Streaming responses (SSE or WebSocket)
- Source citation highlights (hover shows snippet)
- Copy message button
- Regenerate response button
- Follow-up suggestions based on context

---

### 4. Studio Panel (MVP)

**UI:** Right panel - document generation tools

**Generation Types:**

| Type | Description | LlamaIndex Implementation |
|------|-------------|--------------------------|
| **Summary** | High-level overview of all sources | TreeSummarize with chunk synthesis |
| **Study Guide** | Key concepts, terms, questions | Structured extraction + formatting |
| **FAQ** | Auto-generated Q&A pairs | Question generation + answer synthesis |
| **Briefing Doc** | Executive summary with sections | Hierarchical summarization |

**Data Model:**

```typescript
interface StudioDocument {
  id: string;
  notebookId: string;
  type: 'summary' | 'study_guide' | 'faq' | 'briefing';
  title: string;
  content: string; // Markdown
  status: 'generating' | 'ready' | 'failed';
  generatedAt: Date;
}
```

**Backend:**
- `POST /api/notebooks/:id/studio/generate` - Generate document (async job)
- `GET /api/notebooks/:id/studio/:docId` - Get generated document
- `GET /api/notebooks/:id/studio/:docId/status` - Poll generation status

**Generation Pipeline:**
1. User clicks "Generate Summary"
2. Create `StudioDocument` record (status: generating)
3. Dispatch to generation worker (Redis queue)
4. Worker: Load all chunks from Qdrant (namespace filter)
5. Worker: LlamaIndex `TreeSummarize` or custom synthesis
6. Worker: Format as Markdown
7. Update `StudioDocument` (status: ready, content: markdown)
8. Frontend polls status, displays result

**LlamaIndex Implementation:**

```python
# packages/retrieval/studio/generators.py
from llama_index.core.response_synthesizers import TreeSummarize

class StudioGenerator:
    async def generate_summary(self, notebook_id: str) -> str:
        # Load all chunks
        nodes = await self._load_all_nodes(notebook_id)

        # Tree summarize
        synthesizer = TreeSummarize(llm=self.llm)
        summary = await synthesizer.asynthesize(
            query="Provide a comprehensive summary of all content",
            nodes=nodes
        )

        return summary.response

    async def generate_study_guide(self, notebook_id: str) -> str:
        nodes = await self._load_all_nodes(notebook_id)

        # Extract key concepts
        concepts = await self._extract_concepts(nodes)

        # Generate questions
        questions = await self._generate_questions(concepts)

        # Format as markdown
        return self._format_study_guide(concepts, questions)
```

**UI Components:**
- `StudioPanel` - Right panel container
- `StudioTypeSelector` - Buttons for each generation type
- `StudioGenerateButton` - Primary CTA with loading state
- `StudioDocument` - Markdown viewer with export button
- `StudioDocumentCard` - Previously generated docs list

**Features:**
- Markdown preview
- Copy to clipboard
- Download as PDF/DOCX (future)
- Regenerate with different focus (prompt customization)

---

### 5. Three-Panel Layout (MVP)

**Desktop Layout:**

```text
┌─────────────────────────────────────────────────────────────────┐
│ Header (Logo, Notebook Name, User Menu)                         │
├──────────┬────────────────────────────────┬─────────────────────┤
│          │                                │                     │
│ Sources  │         Chat                   │      Studio         │
│ (20%)    │         (50%)                  │      (30%)          │
│          │                                │                     │
│ [+] Add  │  ┌──────────────────────────┐  │  [ ] Summary        │
│          │  │ User: Question?          │  │  [ ] Study Guide    │
│ □ doc.pdf│  └──────────────────────────┘  │  [ ] FAQ            │
│ □ web    │                                │  [ ] Briefing       │
│ □ github │  ┌──────────────────────────┐  │                     │
│          │  │ Assistant: Response...   │  │  [Generate]         │
│          │  │ Sources: [1] [2]         │  │                     │
│          │  └──────────────────────────┘  │  Recent:            │
│          │                                │  · Summary (2h ago) │
│          │  [Type your question...]       │                     │
└──────────┴────────────────────────────────┴─────────────────────┘
```

**Mobile Layout:**
- Tab navigation (Sources | Chat | Studio)
- Bottom sheet for source upload
- Sticky chat input

**UI Components:**
- `NotebookLayout` - Three-panel container with resizable panels
- `PanelResizer` - Drag handle between panels
- `MobileTabNav` - Bottom tab bar for mobile

**Responsive Breakpoints:**
- Desktop (≥1024px): Three panels visible
- Tablet (768-1023px): Two panels (Sources + Chat or Chat + Studio)
- Mobile (<768px): Single panel with tabs

---

## Backend Architecture

### API Structure

```text
apps/api/
├── routes/
│   ├── notebooks.py         # CRUD for notebooks
│   ├── sources.py            # Source upload/management
│   ├── chat.py               # Query endpoint (streaming)
│   └── studio.py             # Document generation
├── services/
│   ├── notebook_service.py   # Business logic
│   ├── ingestion_service.py  # Dispatch to workers
│   └── query_service.py      # LlamaIndex query engine wrapper
└── workers/
    ├── ingest_worker.py      # Process sources
    ├── extract_worker.py     # Extraction pipeline
    └── studio_worker.py      # Document generation
```

### Worker Queue (Redis)

```python
# Job types
INGEST_SOURCE = "ingest:source"       # Process uploaded source
EXTRACT_ENTITIES = "extract:entities" # Run extraction
GENERATE_STUDIO = "studio:generate"   # Generate document

# Queue priorities
QUEUE_HIGH = "queue:high"    # Interactive queries
QUEUE_NORMAL = "queue:normal" # Source processing
QUEUE_LOW = "queue:low"       # Studio generation
```

### Namespacing Strategy

**Qdrant Collections:**
- `taboot_vectors` - Single collection
- Metadata filter: `{"notebook_id": "xxx"}`
- Points tagged with `notebook_id` field

**Neo4j Graph:**
- All nodes have `namespace` property
- Queries always filter: `WHERE n.namespace = $notebook_id`
- Indexes on `(namespace, type)` for performance

**Benefits:**
- Multi-tenancy without collection/graph proliferation
- Efficient filtering
- Easy notebook deletion (delete by namespace)

---

## Data Flow Diagrams

### Source Upload Flow

```text
User uploads PDF
    ↓
POST /api/notebooks/123/sources/upload
    ↓
Create Source record (status: uploading)
    ↓
Store file in object storage / temp
    ↓
Enqueue job: INGEST_SOURCE
    ↓
Return Source ID + polling endpoint
    ↓
[Worker] packages/ingest → normalize → chunk
    ↓
[Worker] TEI embeddings
    ↓
[Worker] Qdrant upsert (namespace: notebook_123)
    ↓
[Worker] Enqueue: EXTRACT_ENTITIES (async)
    ↓
[Worker] Update Source (status: ready)
    ↓
Frontend polls → receives ready status → shows checkmark
```

### Chat Query Flow

```text
User types question
    ↓
POST /api/notebooks/123/chat (SSE)
    ↓
Query service → NotebookQueryEngine
    ↓
TEI embedding of query
    ↓
Qdrant search (filter: notebook_id=123, top_k=20)
    ↓
Rerank (top_k=5)
    ↓
Neo4j graph traversal (2-hop from chunks)
    ↓
Build context with sources
    ↓
LLM streaming (Qwen3-4B)
    ↓
SSE chunks → Frontend
    ↓
Extract citations → Return with response
    ↓
Frontend renders message + citation badges
```

### Studio Generation Flow

```text
User clicks "Generate Summary"
    ↓
POST /api/notebooks/123/studio/generate {type: "summary"}
    ↓
Create StudioDocument (status: generating)
    ↓
Enqueue job: GENERATE_STUDIO
    ↓
Return document ID + polling endpoint
    ↓
[Worker] Load all chunks (Qdrant filter: notebook_123)
    ↓
[Worker] LlamaIndex TreeSummarize
    ↓
[Worker] Format as Markdown
    ↓
[Worker] Update StudioDocument (status: ready, content: md)
    ↓
Frontend polls → displays document
```

---

## MVP Scope

### Phase 1: Core Structure (Week 1)
- [ ] Notebook CRUD (backend + frontend)
- [ ] Three-panel layout with resizable panels
- [ ] Empty states for all panels
- [ ] Mobile responsive tabs

### Phase 2: Source Management (Week 2)
- [ ] File upload (PDF, text, markdown)
- [ ] URL ingestion (web, YouTube)
- [ ] Source list UI with status indicators
- [ ] Processing pipeline integration
- [ ] Source deletion

### Phase 3: Chat (Week 3)
- [ ] Chat message UI (bubbles, citations)
- [ ] Query endpoint with streaming
- [ ] LlamaIndex hybrid retriever integration
- [ ] Source citation display
- [ ] Suggested questions

### Phase 4: Studio (Week 4)
- [ ] Summary generation
- [ ] Study guide generation
- [ ] FAQ generation
- [ ] Markdown viewer
- [ ] Export functionality

### Phase 5: Polish (Week 5)
- [ ] Loading states everywhere
- [ ] Error boundaries
- [ ] Keyboard shortcuts
- [ ] Mobile optimization
- [ ] Onboarding flow

---

## Non-MVP Features (Future)

### Audio Overview (Phase 6+)
- TTS pipeline (OpenAI TTS or ElevenLabs)
- Two-voice dialogue generation
- Downloadable MP3
- Customizable focus/tone
- Interactive audio (interrupt, ask questions)

### Advanced Features
- [ ] Shared notebooks (collaboration)
- [ ] Notebook templates
- [ ] Custom instructions per notebook
- [ ] Export entire notebook
- [ ] Source version history
- [ ] Advanced search/filters
- [ ] Mind map visualization (D3.js + Neo4j)
- [ ] Notebook analytics

### Integrations
- [ ] Google Drive picker
- [ ] Dropbox integration
- [ ] Notion import
- [ ] Obsidian sync
- [ ] Slack bot

---

## UI/UX Patterns (NotebookLM-inspired)

### Design Principles
1. **Sources as first-class citizens** - Always visible in left panel
2. **Zero-latency interactions** - Optimistic updates, background processing
3. **Citation-first** - Every answer links to source material
4. **Progressive disclosure** - Start simple (chat), reveal power features (studio)
5. **Single notebook focus** - No sidebar clutter, one notebook at a time

### Key UX Flows

**New User Onboarding:**
1. Create first notebook (prompt for name)
2. Add first source (drag-drop or URL)
3. See processing status
4. Suggested first question appears
5. Click suggestion → see response with citations
6. Discover studio panel via callout

**Power User Flow:**
1. Quick notebook creation (Cmd+N)
2. Bulk source upload (multi-file select)
3. Ask complex multi-part question
4. Refine with follow-ups
5. Generate study guide for deep dive
6. Export to Markdown

### Keyboard Shortcuts
- `Cmd+N` - New notebook
- `Cmd+K` - Add source
- `Cmd+/` - Focus chat input
- `Cmd+G` - Generate summary
- `Cmd+E` - Export document
- `Cmd+,` - Settings

---

## shadcn/ui Component Mapping

### Pages
- `app/(default)/notebooks/page.tsx` - Notebook list/grid
- `app/(default)/notebooks/[id]/page.tsx` - Three-panel layout

### Components

```text
components/
├── notebook/
│   ├── notebook-card.tsx          # Card component
│   ├── notebook-list.tsx          # List view
│   ├── create-notebook-dialog.tsx # Create modal
│   └── notebook-settings.tsx      # Settings dialog
├── sources/
│   ├── source-panel.tsx           # Left panel container
│   ├── source-card.tsx            # Source item
│   ├── add-source-dialog.tsx      # Upload/URL/Paste tabs
│   ├── source-upload-zone.tsx     # Drag-drop area
│   └── source-status-badge.tsx    # Processing indicator
├── chat/
│   ├── chat-panel.tsx             # Center panel
│   ├── chat-message.tsx           # Message bubble
│   ├── chat-input.tsx             # Textarea + send
│   ├── source-citation.tsx        # Citation badge
│   └── suggested-questions.tsx    # Starter questions
├── studio/
│   ├── studio-panel.tsx           # Right panel
│   ├── studio-type-selector.tsx   # Generation buttons
│   ├── studio-document.tsx        # Markdown viewer
│   └── studio-document-card.tsx   # History item
└── layout/
    ├── notebook-layout.tsx        # Three-panel wrapper
    ├── panel-resizer.tsx          # Drag handle
    └── mobile-tab-nav.tsx         # Mobile tabs
```

### shadcn/ui Components Used
- `Button` - Primary actions
- `Card` - Notebook cards, source cards
- `Dialog` - Modals for create/settings
- `Tabs` - Add source dialog, mobile nav
- `Badge` - Source status, citations
- `Separator` - Panel dividers
- `Textarea` - Chat input
- `ScrollArea` - Message lists
- `DropdownMenu` - Source actions, user menu
- `Progress` - Upload progress
- `Skeleton` - Loading states
- `Sheet` - Mobile panels
- `Tooltip` - Icon explanations

---

## Technical Decisions

### Why LlamaIndex?
- **Framework alignment** - Already used in `packages/retrieval`
- **Hybrid retrieval** - Built-in vector + graph retrievers
- **Streaming support** - Native async/await with streaming
- **Reranking** - First-class reranker integration
- **Flexibility** - Can swap LLMs, vector stores, graph DBs

### Why Not Build Chat from Scratch?
- **Citation extraction** - LlamaIndex handles source tracking
- **Prompt engineering** - Tested prompt templates
- **Context management** - Smart chunking and context windows
- **Extensibility** - Easy to add query transformations, tools

### State Management
- **React Query** - Server state (notebooks, sources, chats)
- **Zustand** (optional) - UI state (panel sizes, selected source)
- **React Context** - Theme, auth

### Real-time Updates
- **SSE** - Chat streaming responses
- **Polling** - Source processing status (5s interval)
- **WebSocket** (future) - Live collaboration

---

## Performance Targets

### Load Times
- Notebook list: <500ms
- Notebook open: <1s (with cached sources)
- Source upload: <3s (small file) to background job (large)
- Chat response (TTFB): <500ms
- Chat response (complete): <3s (p95)
- Studio generation: <30s (summary), <60s (study guide)

### Scalability
- 50 notebooks per user (free tier)
- 50 sources per notebook
- 10K chunks per notebook (500K words × 50 sources ÷ 500 words/chunk)
- 100 concurrent chat requests (p95 latency <3s)

### Resource Usage
- Qdrant: 10GB vectors (10M 1024-dim vectors)
- Neo4j: 5GB graph (1M nodes, 5M relationships)
- Redis: 1GB queue + cache
- Object storage: 100GB uploaded files

---

## Testing Strategy

### Unit Tests
- [ ] Notebook service CRUD
- [ ] Source upload handling
- [ ] Query engine retrieval
- [ ] Citation extraction
- [ ] Studio generators

### Integration Tests
- [ ] End-to-end source processing
- [ ] Chat query with citations
- [ ] Studio document generation
- [ ] Namespace isolation (multi-notebook)

### E2E Tests (Playwright)
- [ ] Create notebook → upload source → ask question → verify citation
- [ ] Generate study guide → verify format
- [ ] Mobile: Upload source via camera (future)

---

## Migration from Current State

### What to Keep
- ✅ Auth system (Better Auth, OAuth, 2FA)
- ✅ Settings pages
- ✅ User management
- ✅ shadcn/ui theme system

### What to Replace
- 🔄 Dashboard page → Notebook list
- 🔄 Empty profile page → User settings (keep minimal)
- 🔄 API test page → Remove (debug via devtools)

### New Routes

```text
/notebooks               → Notebook list (new default)
/notebooks/[id]          → Three-panel notebook view
/notebooks/[id]/settings → Notebook settings
```

### Database Schema (PostgreSQL via Prisma)

```prisma
model Notebook {
  id          String   @id @default(cuid())
  name        String
  description String?
  namespace   String   @unique // For Neo4j/Qdrant filtering
  userId      String
  user        User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  sources     Source[]
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Source {
  id           String   @id @default(cuid())
  notebookId   String
  notebook     Notebook @relation(fields: [notebookId], references: [id], onDelete: Cascade)
  type         String   // pdf, text, web, youtube, github, audio
  name         String
  url          String?
  filePath     String?  // Object storage key
  fileSize     Int?
  wordCount    Int      @default(0)
  status       String   @default("uploading") // uploading, processing, ready, failed
  error        String?
  uploadedAt   DateTime @default(now())
  processedAt  DateTime?
}

model StudioDocument {
  id          String   @id @default(cuid())
  notebookId  String
  type        String   // summary, study_guide, faq, briefing
  title       String
  content     String   @db.Text
  status      String   @default("generating")
  generatedAt DateTime @default(now())
}
```

---

## Success Metrics

### User Engagement
- Daily active users
- Notebooks created per user
- Sources uploaded per notebook
- Questions asked per session
- Studio documents generated

### Performance
- P95 chat response time <3s
- Source processing success rate >98%
- Zero citation hallucinations (strict grounding)

### Quality
- User thumbs up/down on responses
- Citation click-through rate
- Studio document downloads

---

## Open Questions

1. **File storage:** Local disk, S3-compatible, or PostgreSQL BYTEA?
   - **Recommendation:** S3-compatible (MinIO locally, S3 in prod)

2. **Chat history:** Store in PostgreSQL or Redis?
   - **Recommendation:** PostgreSQL for persistence, Redis for session cache

3. **Streaming protocol:** SSE or WebSocket?
   - **Recommendation:** SSE (simpler, HTTP/2 compatible)

4. **Mobile app:** PWA or native?
   - **Recommendation:** PWA first (NotebookLM launched web-first)

5. **Audio overview priority:**
   - **Recommendation:** Post-MVP (high effort, low initial value)

---

## Next Steps

1. **Finalize scope** - Confirm MVP features
2. **Schema review** - Validate Prisma models
3. **API spec** - OpenAPI schema for all endpoints
4. **UI mockups** - Figma wireframes for three-panel layout
5. **Backend setup** - Notebook/Source CRUD endpoints
6. **Frontend scaffolding** - Page structure, routing, empty states
7. **Ingestion integration** - Wire up existing packages
8. **Query engine** - LlamaIndex NotebookQueryEngine implementation
9. **Iterate** - Build → test → refine

**Target:** Functional MVP in 4-5 weeks
