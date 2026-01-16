import { useMemo, useState } from "react"
import { useSearchParams } from "react-router"
import dayjs from "dayjs"
import { Plus, Search, Eye, EyeOff } from "lucide-react"
import { toast } from "sonner"
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  flexRender,
  functionalUpdate,
  getCoreRowModel,
  type PaginationState,
  type ColumnDef,
  useReactTable,
} from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from "@/components/ui/pagination"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { createUserAdminApiAdminUsersCreatePost, getUsersApiAdminUsersGet, setRoleApiAdminUsersSetRolePost, deleteUserAdminApiAdminUsersDeletePost } from "@/APIs"
import type { UserResponse } from "@/APIs/types.gen"

type AdminUsersParams = {
  page: number
  pageSize: number
  keyword: string
  role: string
}

function parsePositiveInt(raw: string | null, fallback: number) {
  if (raw == null) return fallback
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

function normalizeRole(value: string | null) {
  if (!value) return "all"
  if (value === "admin" || value === "user") return value
  return "all"
}

export default function AdminUsers() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<UserResponse | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [newUser, setNewUser] = useState<{ username: string; password: string; role: string }>({
    username: "",
    password: "123456",
    role: "user",
  })

  const params = useMemo<AdminUsersParams>(() => {
    const defaults: AdminUsersParams = {
      page: 1,
      pageSize: 10,
      keyword: "",
      role: "all",
    }

    return {
      ...defaults,
      page: parsePositiveInt(searchParams.get("page"), defaults.page),
      pageSize: parsePositiveInt(searchParams.get("page_size"), defaults.pageSize),
      keyword: searchParams.get("keyword") ?? defaults.keyword,
      role: normalizeRole(searchParams.get("role")),
    }
  }, [searchParams])

  const onParamsChange = (next: AdminUsersParams) => {
    setSearchParams((prev) => {
      const nextSearchParams = new URLSearchParams(prev)
      nextSearchParams.set("page", String(next.page))
      nextSearchParams.set("page_size", String(next.pageSize))
      if (next.keyword) nextSearchParams.set("keyword", next.keyword)
      else nextSearchParams.delete("keyword")
      if (next.role && next.role !== "all") nextSearchParams.set("role", next.role)
      else nextSearchParams.delete("role")
      return nextSearchParams
    })
  }

  const query = useMemo(() => {
    const nextQuery: Record<string, unknown> = {
      page: params.page,
      page_size: params.pageSize,
    }
    if (params.keyword) nextQuery.keyword = params.keyword
    if (params.role && params.role !== "all") nextQuery.role = params.role
    return nextQuery
  }, [params.keyword, params.page, params.pageSize, params.role])

  const usersQuery = useQuery({
    queryKey: ["adminUsers", query],
    queryFn: async () => getUsersApiAdminUsersGet({ query, throwOnError: true }),
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  })

  const createUserMutation = useMutation({
    mutationFn: async (input: { username: string; password: string; role: string }) => {
      const { data, error: apiError } = await createUserAdminApiAdminUsersCreatePost({
        body: input,
      })
      if (apiError) throw new Error("创建失败，请检查输入后重试")
      if (data && data.code >= 300) throw new Error(data.err_msg || "创建失败")
      return data
    },
    onSuccess: async () => {
      toast("用户已创建")
      setCreateDialogOpen(false)
      setNewUser({ username: "", password: "123456", role: "user" })
      await queryClient.invalidateQueries({ queryKey: ["adminUsers"] })
    },
    onError: (err) => {
      toast("创建用户失败", {
        description: err instanceof Error ? err.message : "发生未知错误",
      })
    },
  })

  const setRoleMutation = useMutation({
    mutationFn: async (input: { userId: string; role: string }) => {
      const { data, error: apiError } = await setRoleApiAdminUsersSetRolePost({
        query: { user_id: input.userId },
        body: { role: input.role },
      })
      if (apiError) throw new Error("设置角色失败，请重试")
      if (data && data.code >= 300) throw new Error(data.err_msg || "设置角色失败")
      return input
    },
    onMutate: async (input) => {
      await queryClient.cancelQueries({ queryKey: ["adminUsers"] })

      const previous = queryClient.getQueriesData({ queryKey: ["adminUsers"] })

      queryClient.setQueriesData({ queryKey: ["adminUsers"] }, (old) => {
        if (!old) return old
        if (typeof old !== "object") return old
        const oldAny = old as any
        const items: UserResponse[] | undefined = oldAny?.data?.data?.items
        if (!Array.isArray(items)) return old

        const nextItems = items.map((u) => (u.id === input.userId ? { ...u, role: input.role } : u))
        return {
          ...oldAny,
          data: {
            ...oldAny.data,
            data: {
              ...oldAny.data.data,
              items: nextItems,
            },
          },
        }
      })

      return { previous }
    },
    onError: (err, _input, context) => {
      context?.previous?.forEach(([key, data]) => {
        queryClient.setQueryData(key, data)
      })
      toast("设置角色失败", {
        description: err instanceof Error ? err.message : "发生未知错误",
      })
    },
    onSuccess: () => {
      toast("角色已更新")
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: ["adminUsers"] })
    },
  })

  const deleteUserMutation = useMutation({
    mutationFn: async (userId: string) => {
      const { data, error: apiError } = await deleteUserAdminApiAdminUsersDeletePost({
        query: { user_id: userId },
      })
      if (apiError) throw new Error("删除失败，请重试")
      if (data && data.code >= 300) throw new Error(data.err_msg || "删除失败")
      return userId
    },
    onSuccess: async () => {
      toast("用户已删除")
      setDeleteDialogOpen(false)
      setDeleteTarget(null)
      await queryClient.invalidateQueries({ queryKey: ["adminUsers"] })
    },
    onError: (err) => {
      toast("删除用户失败", {
        description: err instanceof Error ? err.message : "发生未知错误",
      })
    },
  })

  const response = usersQuery.data?.data
  const list = response?.data
  const users = (list?.items ?? []) as UserResponse[]
  const total = list?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / params.pageSize))

  const columns = useMemo<ColumnDef<UserResponse>[]>(() => {
    return [
      {
        accessorKey: "username",
        header: "用户名",
        cell: ({ row }) => <div className="font-medium">{row.original.username}</div>,
      },
      {
        id: "role",
        header: "角色",
        cell: ({ row }) => {
          const user = row.original
          const currentRole = user.role === "admin" || user.role === "user" ? user.role : "user"
          const isUpdating =
            setRoleMutation.isPending &&
            setRoleMutation.variables?.userId === user.id

          return (
            <Select
              value={currentRole}
              disabled={isUpdating}
              onValueChange={(role) => setRoleMutation.mutate({ userId: user.id, role })}
            >
              <SelectTrigger className="w-[120px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">admin</SelectItem>
                <SelectItem value="user">user</SelectItem>
              </SelectContent>
            </Select>
          )
        },
      },
      {
        accessorKey: "created_at",
        header: "创建时间",
        cell: ({ row }) => (
          <div className="text-muted-foreground">
            {row.original.created_at ? dayjs(row.original.created_at).format("YYYY-MM-DD HH:mm") : "-"}
          </div>
        ),
      },
      {
        id: "actions",
        header: "操作",
        cell: ({ row }) => {
          const user = row.original
          const isDeleting = deleteUserMutation.isPending && deleteUserMutation.variables === user.id

          return (
            <Button
              className="cursor-pointer"
              type="button"
              variant="destructive"
              size="sm"
              disabled={isDeleting}
              onClick={() => {
                setDeleteTarget(user)
                setDeleteDialogOpen(true)
              }}
            >
              {isDeleting ? "删除中..." : "删除"}
            </Button>
          )
        },
      },
    
    ]
  }, [deleteUserMutation.isPending, deleteUserMutation.variables, setRoleMutation.isPending, setRoleMutation.variables])

  const table = useReactTable({
    data: users,
    columns,
    getRowId: (row) => row.id,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: totalPages,
    state: {
      pagination: {
        pageIndex: params.page - 1,
        pageSize: params.pageSize,
      },
    },
    onPaginationChange: (updater) => {
      const current: PaginationState = {
        pageIndex: params.page - 1,
        pageSize: params.pageSize,
      }
      const next = functionalUpdate(updater, current)
      onParamsChange({
        ...params,
        page: next.pageIndex + 1,
        pageSize: next.pageSize,
      })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <h1 className="text-2xl font-bold">用户管理</h1>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className=" h-4 w-4" />新建用户
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新建用户</DialogTitle>
              <DialogDescription>创建一个新的用户账号。</DialogDescription>
            </DialogHeader>

            <form
              className="grid gap-4 py-4"
              onSubmit={(e) => {
                e.preventDefault()
                createUserMutation.mutate({
                  username: newUser.username.trim(),
                  password: newUser.password,
                  role: newUser.role,
                })
              }}
            >
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="username" className="text-right">
                  用户名
                </Label>
                <Input
                  id="username"
                  className="col-span-3"
                  value={newUser.username}
                  onChange={(e) => setNewUser((prev) => ({ ...prev, username: e.target.value }))}
                  required
                />
              </div>

              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="password" className="text-right">
                  密码
                </Label>
                <div className="col-span-3 relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    className="pr-10"
                    value={newUser.password}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, password: e.target.value }))}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="role" className="text-right">
                  角色
                </Label>
                <Select
                  value={newUser.role}
                  onValueChange={(role) => setNewUser((prev) => ({ ...prev, role }))}
                >
                  <SelectTrigger className="col-span-3">
                    <SelectValue placeholder="选择角色" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">user</SelectItem>
                    <SelectItem value="admin">admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <DialogFooter>
                <Button type="submit" disabled={createUserMutation.isPending}>
                  {createUserMutation.isPending ? "创建中..." : "保存"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        <Dialog
          open={deleteDialogOpen}
          onOpenChange={(open) => {
            setDeleteDialogOpen(open)
            if (!open) setDeleteTarget(null)
          }}
        >
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>确认删除用户？</DialogTitle>
              <DialogDescription>
                {deleteTarget
                  ? `将永久删除用户 “${deleteTarget.username}”，此操作不可撤销。`
                  : "此操作不可撤销。"}
              </DialogDescription>
            </DialogHeader>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                disabled={deleteUserMutation.isPending}
                onClick={() => setDeleteDialogOpen(false)}
              >
                取消
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={!deleteTarget || deleteUserMutation.isPending}
                onClick={() => {
                  if (!deleteTarget) return
                  deleteUserMutation.mutate(deleteTarget.id)
                }}
              >
                {deleteUserMutation.isPending ? "删除中..." : "确认删除"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <CardTitle>用户列表</CardTitle>
            <div className="flex flex-col md:flex-row md:items-center gap-2 w-full md:w-auto">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索用户名..."
                  className="h-8 w-full md:w-[220px]"
                  value={params.keyword}
                  onChange={(e) =>
                    onParamsChange({
                      ...params,
                      page: 1,
                      keyword: e.target.value,
                    })
                  }
                />
              </div>

              <Select
                value={params.role}
                onValueChange={(role) =>
                  onParamsChange({
                    ...params,
                    page: 1,
                    role,
                  })
                }
              >
                <SelectTrigger className="h-8 w-full md:w-[160px]">
                  <SelectValue placeholder="角色筛选" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部角色</SelectItem>
                  <SelectItem value="admin">admin</SelectItem>
                  <SelectItem value="user">user</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {usersQuery.isLoading ? (
            <div className="text-sm text-muted-foreground">加载中...</div>
          ) : usersQuery.isError ? (
            <div className="space-y-3">
              <div className="text-sm text-destructive">{String(usersQuery.error)}</div>
              <Button type="button" variant="outline" onClick={() => usersQuery.refetch()}>
                重试
              </Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableHead key={header.id}>
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>

                <TableBody>
                  {table.getRowModel().rows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                        暂无数据
                      </TableCell>
                    </TableRow>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <TableRow key={row.id}>
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id}>
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="text-sm text-muted-foreground">
                  共 {total} 条，当前第 {params.page} / {totalPages} 页
                </div>

                <div className="flex items-center gap-3">
                  <Select
                    value={String(params.pageSize)}
                    onValueChange={(value) =>
                      onParamsChange({
                        ...params,
                        page: 1,
                        pageSize: Number(value),
                      })
                    }
                  >
                    <SelectTrigger className="h-8 w-[140px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="5">每页 5</SelectItem>
                      <SelectItem value="10">每页 10</SelectItem>
                      <SelectItem value="20">每页 20</SelectItem>
                      <SelectItem value="50">每页 50</SelectItem>
                    </SelectContent>
                  </Select>

                  <Pagination className="mx-0 w-auto justify-start">
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          href="#"
                          onClick={(e) => {
                            e.preventDefault()
                            if (params.page <= 1) return
                            table.previousPage()
                          }}
                          className={params.page <= 1 ? "pointer-events-none opacity-50" : ""}
                        />
                      </PaginationItem>
                      <PaginationItem>
                        <PaginationNext
                          href="#"
                          onClick={(e) => {
                            e.preventDefault()
                            if (params.page >= totalPages) return
                            table.nextPage()
                          }}
                          className={params.page >= totalPages ? "pointer-events-none opacity-50" : ""}
                        />
                      </PaginationItem>
                    </PaginationContent>
                  </Pagination>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
