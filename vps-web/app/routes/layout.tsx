import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Outlet } from "react-router";
import { Header } from "@/components/header";

export default function Layout() {
  return (
    <SidebarProvider >
      <AppSidebar />
      <SidebarInset className="overflow-hidden">
        <Header />
        <div className="flex-1 overflow-y-auto p-4">
            <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
