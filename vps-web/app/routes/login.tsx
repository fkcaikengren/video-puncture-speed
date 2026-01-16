import { useActionState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useNavigate } from "react-router"
import { loginApiAuthLoginPost } from "@/APIs"
import { useAuthStore } from "@/store/useAuthStore"
import loginDec from "@/assets/login_dec.png"
import { z } from "zod";
import { zfd } from "zod-form-data";
import { VideoStatusEnum } from "@/types/video";



const schema = zfd.formData({
  username: zfd.text(z.string().nonempty('用户名不能为空')),
  password: zfd.text(z.string().min(6, '密码不能少于6个字符')),
});

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const [error, handleLogin, loading] = useActionState<string | null, FormData>(async (_prevState, formData) => {
    let payload: z.infer<typeof schema>;
    try {
      payload = schema.parse(formData)
    } catch (error) {
      if (error instanceof z.ZodError) {
        return error.issues.map((issue) => issue.message).join("\n");
      }
      return "发生了未知错误，请稍后重试";
    }

    try {
      const { data, error: apiError } = await loginApiAuthLoginPost({
        body: payload,
      });

      if (apiError) {
        console.error(apiError)
        return "Login failed. Please check your credentials.";
      } else if (data && data.code >= 300) {
        return data?.err_msg || "Unknown error occurred"
      }
      setAuth(data.data.token, data.data.user);
      navigate(`/dashboard?status=${VideoStatusEnum.PENDING}`);
      return null;
    } catch (err) {
      return "An unexpected error occurred. Please try again."
    } 
  }, null);

  return (
    <div className="w-full h-screen bg-gray-200  px-4 py-4">
      <div className="w-full h-full rounded-2xl bg-background lg:grid lg:grid-cols-2 overflow-hidden relative">
        <div className="flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto grid w-[350px] gap-6">
            <div className="grid gap-2 text-center">
              <h1 className="text-5xl font-bold tracking-tighter text-primary mb-2">VPS</h1>
              <p className="text-xl text-muted-foreground mb-4">
                穿刺测速系统 
              </p>
            </div>
            <form action={handleLogin} className="grid gap-4">
              <div className="grid gap-2 text-muted-foreground">
                <Label htmlFor="username">用户名</Label>
                <Input 
                  id="username" 
                  name="username"
                  type="text" 
                  placeholder="admin" 
                  required 
                />
              </div>
              <div className="grid gap-2 text-muted-foreground">
                <div className="flex items-center">
                  <Label htmlFor="password">密码</Label>
                </div>
                <Input 
                  id="password" 
                  name="password"
                  type="password" 
                  required 
                />
              </div>
              {error && (
                <div className="text-sm text-red-500 font-medium">
                  {error}
                </div>
              )}
              <Button className="w-full" type="submit" disabled={loading}>
                {loading ? "登录中..." : "登录"}
              </Button>
            </form>
          </div>
        </div>
        <div className="hidden lg:block h-full w-full relative bg-primary/90">
        </div>
        <img
          className="w-3/5 absolute left-1/2 top-1/2 -translate-x-[15%] -translate-y-1/2 hidden lg:block"
          src={loginDec}
          alt="Login Decoration"
        />
      </div>
    </div>
  )
}
