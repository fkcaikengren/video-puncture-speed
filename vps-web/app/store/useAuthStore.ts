import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserResponse } from '@/APIs/types.gen'

import { client } from '@/APIs/client.gen';

interface AuthState {
  token: string | null | undefined
  user: UserResponse | null | undefined
  setAuth: (token: string, user: UserResponse) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        set({ token, user });
        // 配置全局请求
        client.setConfig({
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      },
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'auth-storage',
    },
  ),
)
