# PRAMAAN-AICTE Frontend

React 18 + TypeScript + Vite + Tailwind CSS v4 frontend for the PRAMAAN-AICTE prototype.

## Setup

```bash
npm install
cp .env.example .env
```

## Development

```bash
npm run dev
```

Serves the app at http://localhost:5173.

## Production build

```bash
npm run build
npm run preview
```

## Tests

```bash
npm run test
```

## Backend integration

The shell consumes the FastAPI service through `VITE_API_BASE_URL` (default `http://localhost:8000`); only the existing `/health` endpoint is used, with unreachable-backend handled as an error state.
