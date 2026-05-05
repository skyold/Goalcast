import { useEffect, useState, useCallback } from "react";
import { Tabs, Drawer, Button, Pagination, Spin, Empty, Badge, Tag } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Prism from "prismjs";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useConfig } from "../config";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import type { JsonRecord, BoardTab, BoardTabSource, DetailTab, ColumnDef } from "../types";

dayjs.extend(relativeTime);

function CellRenderer({ col, value }: { col: ColumnDef; value: unknown }) {
  if (value == null) return <span>—</span>;

  const render = col.render ?? "text";

  switch (render) {
    case "status_badge": {
      const config = col.status_map?.[String(value)];
      if (config) {
        return <Badge color={config.color} text={config.text} />;
      }
      return <Tag>{String(value)}</Tag>;
    }
    case "number_precision": {
      const num = Number(value);
      if (isNaN(num)) return <span>{String(value)}</span>;
      return <span>{num.toFixed(col.precision ?? 2)}</span>;
    }
    case "percentage_color": {
      const num = Number(value);
      if (isNaN(num)) return <span>{String(value)}</span>;
      const color = num >= 0 ? "var(--green)" : "var(--red)";
      return <span style={{ color }}>{(num * 100).toFixed(2)}%</span>;
    }
    case "relative_time": {
      return <span>{dayjs(String(value)).fromNow()}</span>;
    }
    case "date_time": {
      return <span>{dayjs(String(value)).format("YYYY-MM-DD HH:mm:ss")}</span>;
    }
    case "code_snippet": {
      return <code style={{ fontSize: 11, background: "var(--nav-bg)", padding: "2px 4px", borderRadius: 4 }}>{String(value)}</code>;
    }
    default:
      return <span>{String(value)}</span>;
  }
}

function DetailTabRenderer({ tab, data }: { tab: DetailTab; data: Record<string, unknown> }) {
  const content = (getByPath(data, tab.field) as string) || "";

  if (tab.format === "markdown") {
    return (
      <div className="markdown-body" style={{ padding: 16 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  }

  if (tab.format === "code") {
    const html = Prism.highlight(
      content,
      Prism.languages[tab.language || "javascript"] || Prism.languages.javascript,
      tab.language || "javascript"
    );
    return (
      <pre style={{ margin: 0, padding: 16, background: "var(--nav-bg)", overflow: "auto" }}>
        <code dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    );
  }

  if (tab.format === "diff") {
    return (
      <pre style={{ margin: 0, padding: 16, background: "#1a1a1a", color: "#d4d4d4", overflow: "auto" }}>
        <code>{content}</code>
      </pre>
    );
  }

  return (
    <pre style={{ margin: 0, padding: 16, background: "var(--nav-bg)", overflow: "auto" }}>
      <code>{JSON.stringify(data[tab.field] || data, null, 2)}</code>
    </pre>
  );
}

function getByPath(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object") {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export default function BoardPage() {
  const config = useConfig();
  const tabs = config.board.tabs;
  const [activeDir, setActiveDir] = useState(tabs[0]?.dir ?? "");
  const [items, setItems] = useState<JsonRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [drawerRecord, setDrawerRecord] = useState<JsonRecord | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const boardRefreshDirs = useAppStore((s) => s.boardRefreshDirs);
  const consumeBoardRefresh = useAppStore((s) => s.consumeBoardRefresh);
  const injectChatMessage = useAppStore((s) => s.injectChatMessage);

  const PAGE_SIZE = 20;

  const fetchList = useCallback(
    async (dir: string, p: number, source?: BoardTabSource) => {
      setLoading(true);
      try {
        if (source && source.provider === "rest" && source.endpoints?.list) {
          const url = source.endpoints.list;
          const res = await api.getBoardListCustom(url, {
            page: p,
            page_size: PAGE_SIZE,
          });
          const mapping = source.list_response ?? {};
          const items = (res as Record<string, unknown>)[mapping.items ?? "items"] as JsonRecord[];
          setItems(items ?? []);
          setTotal((res as Record<string, unknown>)[mapping.total ?? "total"] as number ?? 0);
        } else {
          const res = await api.getBoardList(dir, { page: p, page_size: PAGE_SIZE });
          setItems(res.items);
          setTotal(res.total);
        }
      } catch {
        setItems([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (activeDir) {
      const tab = tabs.find((t) => t.dir === activeDir);
      fetchList(activeDir, page, tab?.source);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDir, page, fetchList]);

  useEffect(() => {
    if (boardRefreshDirs.includes(activeDir)) {
      const tab = tabs.find((t) => t.dir === activeDir);
      fetchList(activeDir, page, tab?.source);
      consumeBoardRefresh(activeDir);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardRefreshDirs, activeDir, page, fetchList, consumeBoardRefresh]);

  const handleTabChange = (dir: string) => {
    setActiveDir(dir);
    setPage(1);
    setItems([]);
    setSortKey(null);
    setSortOrder("asc");
  };

  const handleSort = (colKey: string) => {
    if (sortKey === colKey) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortKey(colKey);
      setSortOrder("asc");
    }
  };

  const sortedItems = [...items].sort((a, b) => {
    if (!sortKey) return 0;
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return sortOrder === "asc" ? -1 : 1;
    if (bVal == null) return sortOrder === "asc" ? 1 : -1;
    const comparison = typeof aVal === "number" && typeof bVal === "number"
      ? aVal - bVal
      : String(aVal).localeCompare(String(bVal));
    return sortOrder === "asc" ? comparison : -comparison;
  });

  const handleRowClick = async (record: JsonRecord) => {
    setDrawerLoading(true);
    setDrawerRecord(null);
    try {
      const tab = tabs.find((t) => t.dir === activeDir);
      if (tab?.source && tab.source.provider === "rest" && tab.source.endpoints?.detail) {
        const src = tab.source;
        const idValue = String(record[src.id_field] ?? "");
        const url = src.endpoints!.detail
          .replace("{type}", activeDir)
          .replace("{id}", encodeURIComponent(idValue));
        const full = await api.getBoardItemCustom(url);
        setDrawerRecord(full as JsonRecord);
      } else {
        const full = await api.getBoardItem(activeDir, record._filename);
        setDrawerRecord(full);
      }
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleInjectChat = () => {
    if (!drawerRecord) return;
    const tab = tabs.find((t) => t.dir === activeDir);
    if (tab?.source) {
      const idValue = String(drawerRecord[tab.source.id_field] ?? "unknown");
      injectChatMessage(
        `请解读以下数据（${idValue}）：\n\n${JSON.stringify(drawerRecord, null, 2)}`,
      );
    } else {
      const { _filename, ...rest } = drawerRecord;
      injectChatMessage(
        `请解读以下数据（${_filename}）：\n\n${JSON.stringify(rest, null, 2)}`,
      );
    }
  };

  const activeTab = tabs.find((t) => t.dir === activeDir);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Tabs
        activeKey={activeDir}
        onChange={handleTabChange}
        items={tabs.map((t: BoardTab) => ({ key: t.dir, label: t.label }))}
      />

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>
      ) : items.length === 0 ? (
        <Empty description="暂无数据" style={{ padding: 40 }} />
      ) : (
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)", overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--nav-bg)" }}>
                {activeTab?.columns.map((col) => {
                  const isSorted = sortKey === col.key;
                  const sortIcon = isSorted ? (sortOrder === "asc" ? " ↑" : " ↓") : "";
                  return (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      style={{
                        padding: "8px 16px", textAlign: "left",
                        fontSize: 11, fontWeight: 600, color: isSorted ? "var(--accent)" : "var(--text-muted)",
                        textTransform: "uppercase", letterSpacing: "0.06em",
                        borderBottom: "1px solid var(--border)",
                        cursor: "pointer", userSelect: "none",
                        transition: "color 0.15s ease",
                      }}
                    >
                      {col.label}{sortIcon}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((record, i) => {
                const rowKey = activeTab?.source
                  ? String(record[activeTab.source.id_field] ?? i)
                  : record._filename;
                return (
                <tr
                  key={rowKey}
                  style={{ borderBottom: i < items.length - 1 ? "1px solid var(--border-subtle)" : "none" }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--hover-bg)")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
                >
                    {activeTab?.columns.map((col, colIdx) => (
                      <td key={col.key} style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>
                        {colIdx === 0 ? (
                          <span
                            onClick={() => handleRowClick(record)}
                            style={{
                              color: "var(--accent)", cursor: "pointer",
                              borderBottom: "1px dashed var(--accent-border)",
                              fontFamily: "var(--font-mono)", fontSize: 12,
                            }}
                          >
                            <CellRenderer col={col} value={record[col.key]} />
                          </span>
                        ) : (
                          <CellRenderer col={col} value={record[col.key]} />
                        )}
                      </td>
                    ))}

                </tr>
                );
              })}
            </tbody>
          </table>

          {total > PAGE_SIZE && (
            <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", textAlign: "right" }}>
              <Pagination
                current={page}
                total={total}
                pageSize={PAGE_SIZE}
                onChange={setPage}
                size="small"
                showTotal={(t) => `共 ${t} 条`}
              />
            </div>
          )}
        </div>
      )}

      <Drawer
        title={
          drawerRecord
            ? (() => {
                const tab = tabs.find((t) => t.dir === activeDir);
                if (tab?.source) {
                  return String(drawerRecord[tab.source.id_field] ?? "详情");
                }
                return drawerRecord._filename ?? "详情";
              })()
            : "详情"
        }
        placement="right"
        width={600}
        onClose={() => setDrawerRecord(null)}
        open={!!drawerRecord || drawerLoading}
        extra={
          <Button type="primary" size="small" onClick={handleInjectChat} disabled={!drawerRecord}>
            助手解读
          </Button>
        }
      >
        {drawerLoading ? (
          <Spin style={{ display: "block", margin: "40px auto" }} />
        ) : drawerRecord ? (
          (() => {
            const tab = tabs.find((t) => t.dir === activeDir);
            if (tab?.source?.detail.mode === "tabs" && tab.source.detail.tabs?.length) {
              return (
                <Tabs
                  size="small"
                  items={tab.source.detail.tabs.map((dt) => ({
                    key: dt.label,
                    label: dt.label,
                    children: <DetailTabRenderer tab={dt} data={drawerRecord} />,
                  }))}
                />
              );
            }
            return (
              <pre style={{
                background: "#0a0a12", color: "var(--green)",
                padding: 16, borderRadius: 8, fontSize: 12,
                overflowX: "auto", whiteSpace: "pre-wrap",
                border: "1px solid var(--border)",
              }}>
                {JSON.stringify(
                  Object.fromEntries(
                    Object.entries(drawerRecord).filter(([k]) => k !== "_filename"),
                  ),
                  null, 2,
                )}
              </pre>
            );
          })()
        ) : null}
      </Drawer>
    </div>
  );
}
