import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger
} from "@/components/ui/sidebar"
import { Home, Video, Upload, Users, GitCompare } from "lucide-react"
import { Link, useLocation } from "react-router"
import { useAuthStore } from "@/store/useAuthStore"

// Menu items.
const items = [
  {
    title: "首页",
    url: "/dashboard",
    icon: Home,
  },
  {
    title: "视频库",
    url: "/video/list",
    icon: Video,
  },
  {
    title: "分析比较",
    url: "/video/compare",
    icon: GitCompare,
  },
  {
    title: "上传视频",
    url: "/video/upload",
    icon: Upload,
  },
]

const adminItems = [
    {
        title: "User Management",
        url: "/admin/users",
        icon: Users,
    }
]

export function AppSidebar() {
  const location = useLocation();
  const { user, logout } = useAuthStore();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center justify-between px-4 py-2 group-data-[collapsible=icon]:px-0">
          <div className="text-xl font-bold group-data-[collapsible=icon]:hidden">v-puncture</div>
          <SidebarTrigger />
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Application</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={location.pathname === item.url}>
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
            <SidebarGroupLabel>Admin</SidebarGroupLabel>
            <SidebarGroupContent>
                <SidebarMenu>
                {adminItems.map((item) => (
                    <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild isActive={location.pathname === item.url}>
                        <Link to={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                        </Link>
                    </SidebarMenuButton>
                    </SidebarMenuItem>
                ))}
                </SidebarMenu>
            </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  )
}
