import { type RouteConfig, index, route, layout } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("login", "routes/login.tsx"),
  
  layout("routes/layout.tsx", [
    route("dashboard", "routes/dashboard.tsx"),
    route("video/list", "routes/video-list.tsx"),
    route("video/analysis", "routes/video-analysis.tsx"),
    route("video/compare", "routes/video-compare.tsx"),
    route("video/upload", "routes/video-upload.tsx"),
    route("admin/users", "routes/admin-users.tsx"),
  ]),
] satisfies RouteConfig;
