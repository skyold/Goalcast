import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

const defaultConfig = {
  app: { name: "Test App", subtitle: "" },
  modules: { agents: true, board: true, tokens: true, chat: true, logs: true },
  agents: { clusters: [] },
  board: {
    tabs: [
      {
        dir: "hypotheses",
        label: "假想",
        columns: [
          { key: "hypothesis_id", label: "ID" },
          { key: "text", label: "内容" },
          { key: "status", label: "状态" },
        ],
      },
      {
        dir: "factors",
        label: "因子",
        columns: [{ key: "factor_id", label: "ID" }],
      },
    ],
  },
};

const { mockUseConfig } = vi.hoisted(() => ({
  mockUseConfig: vi.fn(() => defaultConfig),
}));

vi.mock("../src/config", () => ({
  useConfig: mockUseConfig,
}));

// Mock API
const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    getBoardList: vi.fn(),
    getBoardItem: vi.fn(),
    getBoardListCustom: vi.fn(),
    getBoardItemCustom: vi.fn(),
  },
}));

vi.mock("../src/services/api", () => ({
  api: mockApi,
}));

// Mock Store
vi.mock("../src/store/appStore", () => ({
  useAppStore: vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      boardRefreshDirs: [],
      isChatOpen: true,
      injectChatMessage: vi.fn(),
      consumeBoardRefresh: vi.fn(),
    })
  ),
}));

import BoardPage from "../src/pages/BoardPage";

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false, media: query, onchange: null,
      addListener: vi.fn(), removeListener: vi.fn(),
      addEventListener: vi.fn(), removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverMock {
    observe() {} unobserve() {} disconnect() {}
  }
  vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  vi.clearAllMocks();
  mockUseConfig.mockReturnValue(defaultConfig);
  mockApi.getBoardList.mockResolvedValue({
    items: [
      { _filename: "HY-001.json", hypothesis_id: "HY-001", text: "test", status: "active" },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  });
  mockApi.getBoardItem.mockResolvedValue({
    _filename: "HY-001.json",
    hypothesis_id: "HY-001",
    text: "full detail",
    status: "active",
    theme: "momentum",
  });
});

describe("BoardPage", () => {
  it("从配置渲染页签", async () => {
    render(<BoardPage />);
    expect(screen.getByRole("tab", { name: /假想/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /因子/i })).toBeInTheDocument();
  });

  it("挂载时请求当前页签的列表数据", async () => {
    render(<BoardPage />);
    await waitFor(() =>
      expect(mockApi.getBoardList).toHaveBeenCalledWith("hypotheses", { page: 1, page_size: 20 })
    );
  });

  it("从配置渲染列标题", async () => {
    render(<BoardPage />);
    await waitFor(() => expect(screen.getByText("内容")).toBeInTheDocument());
    expect(screen.getByText("状态")).toBeInTheDocument();
  });

  it("以纯文本渲染行数据", async () => {
    render(<BoardPage />);
    await waitFor(() => expect(screen.getByText("HY-001")).toBeInTheDocument());
    expect(screen.getByText("test")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("点击第一列值时打开详情抽屉", async () => {
    render(<BoardPage />);
    await waitFor(() => expect(screen.getByText("HY-001")).toBeInTheDocument());
    fireEvent.click(screen.getByText("HY-001"));
    await waitFor(() =>
      expect(mockApi.getBoardItem).toHaveBeenCalledWith("hypotheses", "HY-001.json")
    );
    expect(await screen.findByText(/full detail/)).toBeInTheDocument();
  });

  it("切换页签后请求新目录的数据", async () => {
    render(<BoardPage />);
    fireEvent.click(screen.getByRole("tab", { name: /因子/i }));
    await waitFor(() =>
      expect(mockApi.getBoardList).toHaveBeenCalledWith("factors", { page: 1, page_size: 20 })
    );
  });

  describe("source 模式", () => {
    const sourceConfig = {
      app: { name: "Test App", subtitle: "" },
      modules: { agents: true, board: true, tokens: true, chat: true, logs: true },
      agents: { clusters: [] },
      board: {
        tabs: [
          {
            dir: "factors",
            label: "因子",
            source: {
              type: "directory",
              list_api: "/results/factors",
              detail_api: "/results/{type}/{id}",
              id_field: "factor_id",
              detail: {
                mode: "tabs" as const,
                tabs: [
                  { label: "元数据", field: "detail.md", format: "markdown" as const },
                  { label: "代码", field: "detail.code", format: "code" as const, language: "python" },
                ],
              },
            },
            columns: [
              { key: "factor_id", label: "ID" },
              { key: "name", label: "名称" },
            ],
          },
        ],
      },
    };

    beforeEach(() => {
      mockUseConfig.mockReturnValue(sourceConfig);
      mockApi.getBoardListCustom.mockResolvedValue({
        items: [
          { factor_id: "FA-COMP-001", name: "Amihud", status: "active" },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      });
      mockApi.getBoardItemCustom.mockResolvedValue({
        type: "factor",
        id: "FA-COMP-001",
        detail: {
          md: "## 市场假设\n\nAmihud illiquidity measure.",
          code: "import numpy as np\ndef calculate(df):\n    return df",
        },
      });
    });

    it("source 模式调用 getBoardListCustom 代替 getBoardList", async () => {
      render(<BoardPage />);
      await waitFor(() =>
        expect(mockApi.getBoardListCustom).toHaveBeenCalledWith("/results/factors", {
          page: 1,
          page_size: 20,
        })
      );
      expect(mockApi.getBoardList).not.toHaveBeenCalled();
    });

    it("source 模式点击行调用 getBoardItemCustom 并用占位符替换 URL", async () => {
      render(<BoardPage />);
      await waitFor(() => expect(screen.getByText("FA-COMP-001")).toBeInTheDocument());
      fireEvent.click(screen.getByText("FA-COMP-001"));
      await waitFor(() =>
        expect(mockApi.getBoardItemCustom).toHaveBeenCalledWith(
          "/results/factors/FA-COMP-001"
        )
      );
    });

    it("source 模式 tabs 渲染显示 Markdown 和代码标签页", async () => {
      render(<BoardPage />);
      await waitFor(() => expect(screen.getByText("FA-COMP-001")).toBeInTheDocument());
      fireEvent.click(screen.getByText("FA-COMP-001"));
      await waitFor(() => {
        expect(screen.getByRole("tab", { name: "元数据" })).toBeInTheDocument();
        expect(screen.getByRole("tab", { name: "代码" })).toBeInTheDocument();
      });
    });
  });
});
