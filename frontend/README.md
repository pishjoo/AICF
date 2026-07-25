# AICF v2 Frontend

Next.js 15 frontend for AICF v2.

## Prerequisites

- Node.js 18+
- npm

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build

```bash
npm run build
```

## Environment Variables

Copy `.env.example` to `.env.local` and configure:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

- `app/` - Next.js App Router pages
- `components/` - React components
  - `ui/` - UI components (shadcn/ui)
  - `layout/` - Layout components
- `hooks/` - Custom React hooks
- `lib/` - Utilities and API client
- `providers/` - Context providers
- `stores/` - Zustand state stores
- `styles/` - Global styles
- `types/` - TypeScript types
- `public/` - Static assets
