import { create } from 'zustand';
import type { ItemStatus } from '@/types/api';

type ViewMode = 'table' | 'gallery' | 'split';

interface UIState {
  viewMode: ViewMode;
  statusFilter: ItemStatus | null;
  selectedItemId: string | null;
  
  setViewMode: (mode: ViewMode) => void;
  setStatusFilter: (status: ItemStatus | null) => void;
  setSelectedItem: (id: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  viewMode: 'table',
  statusFilter: null,
  selectedItemId: null,
  
  setViewMode: (mode) => set({ viewMode: mode }),
  setStatusFilter: (status) => set({ statusFilter: status }),
  setSelectedItem: (id) => set({ selectedItemId: id }),
}));
