import { Suspense, useState } from "react";
import { Await, useLoaderData } from "react-router";
import { toast } from "sonner";
import { useMutation } from "@tanstack/react-query";
import { getProfileApiUserProfileGet, updatePasswordApiUserPasswordPost } from "~/APIs/sdk.gen";
import type { UpdatePasswordRequest, UserResponse } from "~/APIs/types.gen";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Skeleton } from "~/components/ui/skeleton";
import type { Route } from "./+types/profile";

export function meta({}: Route.MetaArgs) {
  return [{ title: "User Profile" }, { name: "description", content: "User Profile Settings" }];
}

export async function clientLoader() {
  const profilePromise = getProfileApiUserProfileGet().then((res) => {
    if (res.error) {
      throw new Error("Failed to load profile");
    }
    const { code = 500, data, err_msg } = res.data || {}
    if(code >=300 ){
      throw new Error(err_msg || "Failed to load profile");
    }
    return data as UserResponse;
  });
  return { profilePromise };
}

function ProfileSkeleton() {
  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-32 mt-2" />
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-10 w-32" />
        </CardContent>
      </Card>
    </div>
  );
}

function ChangePasswordDialog() {
  const [open, setOpen] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { mutate, isPending, error: mutationError } = useMutation({
    mutationFn: async (data: UpdatePasswordRequest) => {
      const { data: responseData, error } = await updatePasswordApiUserPasswordPost({
        body: data,
      });
      if (error) {
        throw error;
      }
      return responseData;
    },
    onSuccess: () => {
      toast.success("密码修改成功");
      setOpen(false);
      setValidationError(null);
    },
    onError: (err: any) => {
      // 错误已经在 UI 中显示，这里可以做额外的处理如果需要
      // console.error(err);
    }
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setValidationError(null);
    
    const formData = new FormData(event.currentTarget);
    const old_password = formData.get("old_password") as string;
    const new_password = formData.get("new_password") as string;
    const confirm_password = formData.get("confirm_password") as string;

    if (new_password !== confirm_password) {
      setValidationError("两次输入的密码不一致");
      return;
    }

    mutate({
      old_password,
      new_password,
    });
  };

  const errorMessage = validationError || (mutationError as any)?.detail || (mutationError ? "修改密码失败" : null);

  return (
    <Dialog open={open} onOpenChange={(open) => {
      setOpen(open);
      if (!open) setValidationError(null);
    }}>
      <DialogTrigger asChild>
        <Button variant="outline">修改密码</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>修改密码</DialogTitle>
          <DialogDescription>
            输入当前密码和新密码以更新您的凭据。
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="old_password">当前密码</Label>
            <Input
              id="old_password"
              name="old_password"
              type="password"
              required
              placeholder="请输入当前密码"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new_password">新密码</Label>
            <Input
              id="new_password"
              name="new_password"
              type="password"
              required
              placeholder="请输入新密码"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm_password">确认新密码</Label>
            <Input
              id="confirm_password"
              name="confirm_password"
              type="password"
              required
              placeholder="请再次输入新密码"
            />
          </div>
          
          {errorMessage && (
            <div className="text-sm text-red-500 font-medium">
              {errorMessage}
            </div>
          )}

          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? "更新中..." : "确认修改"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ProfileContent({ profile }: { profile: UserResponse }) {
  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>我的信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>用户名</Label>
            <div className="p-3 bg-muted rounded-md text-sm font-medium">
              {profile.username}
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>角色</Label>
            <div className="p-3 bg-muted rounded-md text-sm font-medium capitalize">
              {profile.role || "User"}
            </div>
          </div>

          <div className="pt-4">
            <ChangePasswordDialog />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function Profile() {
  const { profilePromise } = useLoaderData<typeof clientLoader>();

  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <Await resolve={profilePromise} errorElement={<div>Failed to load profile</div>}>
        {(profile) => <ProfileContent profile={profile!} />}
      </Await>
    </Suspense>
  );
}
