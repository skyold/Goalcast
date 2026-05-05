import { create } from "zustand";
import type { AgentStatus, PipelineState, Alert, ChatMessage, WsMessage, BoardUpdatePayload } from "../types";

interface MatchCard {
  match_id: string;
  home_team: string;
  away_team: string;
  kickoff_time: string;
  status: "pending" | "analyzing" | "trading" | "done" | "error";
  predictions?: { home_win?: number; draw?: number; away_win?: number };
  ev?: number;
  recommendation?: string;
  error?: string;
}

interface AppState {
  agents: Record<string, AgentStatus>;
  pipelines: PipelineState[];
  alerts: Alert[];
  chatMessages: ChatMessage[];
  isChatOpen: boolean;
  wsConnected: boolean;
  pendingChatInjection: string | null;
  boardRefreshDirs: string[];
  pipelineMatches: Record<string, MatchCard>;
  pipelineStatus: string;
  activeLeagues: string[];

  updateAgent: (agent: AgentStatus) => void;
  updatePipeline: (pipeline: PipelineState) => void;
  addAlert: (alert: Alert) => void;
  dismissAlert: (agentId: string) => void;
  addChatMessage: (msg: ChatMessage) => void;
  toggleChat: () => void;
  setWsConnected: (connected: boolean) => void;
  handleWsMessage: (msg: WsMessage) => void;
  injectChatMessage: (content: string) => void;
  clearChatInjection: () => void;
  consumeBoardRefresh: (dir: string) => void;
}

let chatIdCounter = 0;

export const useAppStore = create<AppState>((set, get) => ({
  agents: {},
  pipelines: [],
  alerts: [],
  chatMessages: [],
  isChatOpen: true,
  wsConnected: false,
  pendingChatInjection: null,
  boardRefreshDirs: [],
  pipelineMatches: {},
  pipelineStatus: "Idle",
  activeLeagues: [],

  updateAgent: (agent) =>
    set((state) => ({
      agents: { ...state.agents, [agent.agent_id]: agent },
    })),

  updatePipeline: (pipeline) =>
    set((state) => {
      const idx = state.pipelines.findIndex((p) => p.pipeline === pipeline.pipeline);
      if (idx >= 0) {
        const next = [...state.pipelines];
        next[idx] = pipeline;
        return { pipelines: next };
      }
      return { pipelines: [...state.pipelines, pipeline] };
    }),

  addAlert: (alert) =>
    set((state) => ({ alerts: [...state.alerts, alert] })),

  dismissAlert: (agentId) =>
    set((state) => ({
      alerts: state.alerts.filter((a) => a.agent_id !== agentId),
    })),

  addChatMessage: (msg) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, msg],
    })),

  toggleChat: () => set((state) => ({ isChatOpen: !state.isChatOpen })),

  setWsConnected: (connected) => set({ wsConnected: connected }),

  injectChatMessage: (content) => set({ pendingChatInjection: content }),

  clearChatInjection: () => set({ pendingChatInjection: null }),

  consumeBoardRefresh: (dir) =>
    set((state) => ({
      boardRefreshDirs: state.boardRefreshDirs.filter((d) => d !== dir),
    })),

  handleWsMessage: (msg) => {
    const store = get();
    switch (msg.type) {
      case "agent_status":
        store.updateAgent(msg.payload as AgentStatus);
        break;
      case "pipeline_progress":
        store.updatePipeline(msg.payload as PipelineState);
        break;
      case "alert":
        store.addAlert(msg.payload as Alert);
        break;
      case "board_update": {
        const bu = msg.payload as BoardUpdatePayload;
        set((state) => ({
          boardRefreshDirs: state.boardRefreshDirs.includes(bu.dir)
            ? state.boardRefreshDirs
            : [...state.boardRefreshDirs, bu.dir],
        }));
        break;
      }
      case "result_created": {
        const rc = msg.payload as { type: string; id: string; name: string };
        store.addChatMessage({
          id: `sys-${++chatIdCounter}`,
          role: "system",
          content: `📦 新${rc.type}入库: ${rc.name} (${rc.id})`,
          timestamp: new Date().toISOString(),
        });
        break;
      }
      case "pipeline_start": {
        const pl = msg.payload as { leagues?: string[]; date?: string };
        set({
          pipelineMatches: {},
          pipelineStatus: "Running...",
          activeLeagues: pl.leagues ?? [],
        });
        break;
      }
      case "matches_found": {
        const mf = msg.payload as { total?: number; matches?: Array<Partial<MatchCard>> };
        const newMatches: Record<string, MatchCard> = {};
        const matchList = mf.matches;
        if (Array.isArray(matchList)) {
          matchList.forEach((item) => {
            if (!item.match_id) return;
            newMatches[item.match_id] = {
              match_id: item.match_id,
              home_team: item.home_team ?? "",
              away_team: item.away_team ?? "",
              kickoff_time: item.kickoff_time ?? "",
              status: "pending",
            };
          });
        }
        set((state) => ({
          pipelineMatches: { ...state.pipelineMatches, ...newMatches },
        }));
        break;
      }
      case "match_step_start": {
        const ms = msg.payload as { match_id?: string; step?: string };
        const matchId = ms.match_id ?? "";
        if (!matchId) break;
        set((state) => {
          const match = state.pipelineMatches[matchId];
          if (!match) return state;
          return {
            pipelineMatches: {
              ...state.pipelineMatches,
              [matchId]: {
                ...match,
                status: ms.step === "analyst" ? "analyzing" : ms.step === "trader" ? "trading" : "analyzing",
              },
            },
          };
        });
        break;
      }
      case "match_result_ready": {
        const mr = msg.payload as {
          match_id?: string;
          predictions?: MatchCard["predictions"];
          ev?: number;
          recommendation?: string;
        };
        const matchId = mr.match_id ?? "";
        if (!matchId) break;
        set((state) => {
          const match = state.pipelineMatches[matchId];
          if (!match) return state;
          return {
            pipelineMatches: {
              ...state.pipelineMatches,
              [matchId]: {
                ...match,
                status: "done",
                predictions: mr.predictions,
                ev: mr.ev,
                recommendation: mr.recommendation,
              },
            },
          };
        });
        break;
      }
      case "match_step_error": {
        const me = msg.payload as { match_id?: string; message?: string };
        const matchId = me.match_id ?? "";
        if (!matchId) break;
        set((state) => {
          const match = state.pipelineMatches[matchId];
          if (!match) return state;
          return {
            pipelineMatches: {
              ...state.pipelineMatches,
              [matchId]: {
                ...match,
                status: "error",
                error: me.message ?? "Unknown error",
              },
            },
          };
        });
        break;
      }
      case "pipeline_complete": {
        set({ pipelineStatus: "Completed" });
        break;
      }
    }
  },
}));
