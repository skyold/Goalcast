import { afterEach, describe, expect, it, vi } from "vitest";

const staticConfig = {
  app: { name: "FAFETS Console", subtitle: "Quant Research System" },
  modules: { agents: true, board: true, tokens: true, chat: true, logs: true },
  agents: {
    clusters: [
      { key: "research", label: "Research", color: "#60a5fa", desc: "假想生成、挖矿、评判、记录" },
    ],
  },
  board: {
    tabs: [
      {
        dir: "hypotheses",
        label: "假想",
        columns: [{ key: "hypothesis_id", label: "ID" }],
      },
    ],
  },
};

const apiConfig = {
  app: { name: "Agent Dashboard", subtitle: "" },
  modules: { agents: true, board: true, tokens: true, chat: true, logs: true },
  agents: { clusters: [] },
  board: { tabs: [] },
};

describe("loadConfig", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it("后端返回空数组时保留静态 clusters 和 tabs", async () => {
    const fetchMock = vi.fn(async (input: string | URL) => {
      const url = String(input);
      if (url === "/config.json") {
        return {
          ok: true,
          json: async () => staticConfig,
        };
      }
      if (url === "/api/config") {
        return {
          ok: true,
          json: async () => apiConfig,
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { getConfig, loadConfig } = await import("../src/config");
    await loadConfig();

    expect(getConfig().app.name).toBe("Agent Dashboard");
    expect(getConfig().agents.clusters).toEqual(staticConfig.agents.clusters);
    expect(getConfig().board.tabs).toEqual(staticConfig.board.tabs);
  });
});
