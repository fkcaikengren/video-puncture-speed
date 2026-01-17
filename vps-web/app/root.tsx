import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import { useState } from "react";
import type { Route } from "./+types/root";
import "./app.css";
import { ThemeProvider } from "@/components/theme-provider"
import { ModalStore, useModal } from '@/lib/react-modal-store';
import { modalMap } from './components/modals';
import { Toaster } from "@/components/ui/sonner"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "sonner";

import { client } from './APIs/client.gen';
import { useAuthStore } from './store/useAuthStore';

// 配置全局请求 START    
client.interceptors.request.use((config) => {
  // 处理全局请求，例如添加全局请求头
  return config;
})
client.interceptors.response.use((response) => {
  if(response.status === 403){
    toast.error('您没有权限访问该资源')
  }
  // 处理全局响应，例如添加全局错误处理
  if (response.status === 401) {
    // 处理未授权错误，例如跳转到登录页
    useAuthStore.getState().logout();
    window.location.href = '/login';
  }
  return response;
})
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
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <ModalStore modalMap={modalMap} destroyOnClose="afterClose">
          <Outlet />
          <Toaster position="bottom-right" />
        </ModalStore>
      </ThemeProvider>
    </QueryClientProvider>
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
