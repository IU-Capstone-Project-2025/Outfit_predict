# Frontend

This directory contains the Next.js application for the Outfit Predict user interface.

## 🛠️ Tech Stack

- **[Next.js](https://nextjs.org/)**: React framework for production.
- **[React](https://reactjs.org/)**: A JavaScript library for building user interfaces.
- **[TypeScript](https://www.typescriptlang.org/)**: Typed superset of JavaScript.
- **[Tailwind CSS](https://tailwindcss.com/)**: A utility-first CSS framework.
- **[shadcn/ui](https://ui.shadcn.com/)**: Re-usable components built using Radix UI and Tailwind CSS.
- **[Zod](https://zod.dev/)**: TypeScript-first schema validation.
- **[React Hook Form](https://react-hook-form.com/)**: Performant, flexible and extensible forms with easy-to-use validation.

## 🚀 Running the Frontend Locally

The frontend is designed to be run as part of the main `docker-compose.yml` setup in the root directory. However, you can run it in standalone mode for development.

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or newer)
- [pnpm](https://pnpm.io/) (or npm/yarn)

### Installation

1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```

2.  Install the dependencies:
    ```bash
    pnpm install
    ```

### Running in Development Mode

1.  Make sure the backend is running (either via Docker or locally) to have access to the API.

2.  Create a `.env.local` file in the `frontend` directory with the following content:
    ```
    NEXT_PUBLIC_API_URL=http://localhost:8000/api
    ```

3.  Start the development server:
    ```bash
    pnpm dev
    ```

The frontend will be available at [http://localhost:3000](http://localhost:3000).

## 📂 Folder Structure

```
frontend/
├── app/                  # Main application source code (App Router)
│   ├── (auth)/           # Authentication-related pages (login, signup)
│   ├── (main)/           # Main application pages (profile, outfits)
│   ├── api/              # API route handlers
│   └── layout.tsx        # Root layout
├── components/           # Shared React components
│   └── ui/               # UI components from shadcn/ui
├── lib/                  # Utility functions and libraries
├── public/               # Static assets (images, fonts)
├── styles/               # Global styles
└── tsconfig.json         # TypeScript configuration
```
