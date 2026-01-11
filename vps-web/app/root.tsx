import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import type { Route } from "./+types/root";
import "./app.css";
import { ThemeProvider } from "@/components/theme-provider"
import { ModalStore, useModal } from '@/lib/react-modal-store';
import { modalMap } from './components/modals';
import { Toaster } from "@/components/ui/sonner"


import { client } from './APIs/client.gen';
import { useAuthStore } from './store/useAuthStore';

console.log('useAuthStore.getState().token', useAuthStore.getState().token)
// 配置全局请求 START      // TODO: 目前问题，login第一次登录后，token为空，导致后续请求失败，这个setConfig的调用时机？
client.setConfig({
  // set default base url for requests
  // baseURL: '',
  // set default headers for requests
  headers: {
    Authorization: `Bearer ${useAuthStore.getState().token || ''}`,
  },
});


// 配置全局请求 END



export const links: Route.LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap",
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}


export default function App() {

  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <ModalStore modalMap={modalMap} destroyOnClose="afterClose">
        <Outlet />
        <Toaster 
          position="bottom-right"
        />
      </ModalStore>
    </ThemeProvider>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error";
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="pt-16 p-4 container mx-auto">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full p-4 overflow-x-auto">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}
