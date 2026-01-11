import { useActionState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useNavigate } from "react-router"
import { loginApiAuthLoginPost } from "@/APIs"
import { useAuthStore } from "@/store/useAuthStore"


import { z } from "zod";
import { zfd } from "zod-form-data";

const schema = zfd.formData({
  username: zfd.text(),
  password: zfd.text(z.string().min(6))
});

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
 

  const [error, handleLogin, loading] = useActionState<string | null, FormData>(async (_prevState, formData) => {
    // const payload = Object.fromEntries(formData.entries()) //禁止这种ts不友好的转换
    const payload = schema.parse(formData)

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
      navigate("/dashboard");
      return null;
    } catch (err) {
      return "An unexpected error occurred. Please try again."
    } 
  }, null);


  return (
    <div className="flex h-screen w-full items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Login</CardTitle>
          <CardDescription>
            Enter your credentials below to login to your account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form action={handleLogin} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="username">Username</Label>
              <Input 
                id="username" 
                name="username"
                type="text" 
                placeholder="admin" 
                required 
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
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
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
            <div className="text-xs text-muted-foreground text-center">
                Registration defaults to <span className="font-semibold">user</span> role.
                <br />
                Admin role is managed by administrators.
            </div>
        </CardFooter>
      </Card>
    </div>
  )
}
