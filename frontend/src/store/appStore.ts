import { create } from "zustand";
import type { PipelineStatus, WsEvent } from "../types";

interface AppState {
  wsConnected: boolean;
  pipelineStatus: PipelineStatus | null;
  lastWsEvent: WsEvent | null;

  setWsConnected: (connected: boolean) => void;
  setPipelineStatus: (status: PipelineStatus) => void;
  handleWsEvent: (event: WsEvent) => void;
}

export const useAppStore = create<AppState>((set) => ({
  wsConnected: false,
  pipelineStatus: null,
  lastWsEvent: null,

  setWsConnected: (connected) => set({ wsConnected: connected }),

  setPipelineStatus: (status) => set({ pipelineStatus: status }),

  handleWsEvent: (event) => {
    set({ lastWsEvent: event });
    if (event.type === "pipeline_start") {
      set((state) => ({
        pipelineStatus: {
          ...(state.pipelineStatus ?? { running: false, last_result: null }),
          running: true,
        },
      }));
    } else if (event.type === "pipeline_complete") {
      set((state) => ({
        pipelineStatus: {
          ...(state.pipelineStatus ?? { running: false, last_result: null }),
          running: false,
          last_result: (event.payload as { result?: AppState["pipelineStatus"] })?.result ?? state.pipelineStatus?.last_result ?? null,
        },
      }));
    }
  },
}));
