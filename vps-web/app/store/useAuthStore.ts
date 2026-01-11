import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserResponse } from '@/APIs/types.gen'

interface AuthState {
  token: string | null
  user: UserResponse | null
  setAuth: (token: string, user: UserResponse) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'auth-storage',
    },
  ),
)
