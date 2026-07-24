import { create } from 'zustand';

interface AuthState {
  user: {
    id: string | null;
    email: string | null;
    name: string | null;
  } | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: { id: string; email: string; name: string } | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
    }),
  setLoading: (loading) => set({ isLoading: loading }),
  logout: () =>
    set({
      user: null,
      isAuthenticated: false,
    }),
}));
