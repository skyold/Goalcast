import { useEffect, useState, useCallback, Fragment } from "react";
import { Tabs, Drawer, Button, Pagination, Spin, Empty, Badge, Tag, message } from "antd";
import { DownOutlined, RightOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Prism from "prismjs";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useConfig } from "../config";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import type { JsonRecord, BoardTab, BoardTabSource, DetailTab, ColumnDef } from "../types";
import { MatchDataPanel } from "../components/MatchSourcePanel";

dayjs.extend(relativeTime);

// ─── Utility ──────────────────────────────────────────────────────────────────

function getByPath(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object") return (acc as Record<string, unknown>)[key];
    return undefined;
  }, obj);
}

// ─── CellRenderer ─────────────────────────────────────────────────────────────

function CellRenderer({ col, value }: { col: ColumnDef; value: unknown }) {
  if (value == null) return <span>—</span>;
  const render = col.render ?? "text";
  switch (render) {
    case "status_badge": {
      const cfg = col.status_map?.[String(value)];
      if (cfg) return <Badge color={cfg.color} text={cfg.text} />;
      return <Tag>{String(value)}</Tag>;
    }
    case "number_precision": {
      const n = Number(value);
      return isNaN(n) ? <span>{String(value)}</span> : <span>{n.toFixed(col.precision ?? 2)}</span>;
    }
    case "percentage_color": {
      const n = Number(value);
      if (isNaN(n)) return <span>{String(value)}</span>;
      return <span style={{ color: n >= 0 ? "var(--green)" : "var(--red)" }}>{(n * 100).toFixed(2)}%</span>;
    }
    case "relative_time": return <span>{dayjs(String(value)).fromNow()}</span>;
    case "date_time": return <span>{dayjs(String(value)).format("YYYY-MM-DD HH:mm:ss")}</span>;
    case "code_snippet":
      return <code style={{ fontSize: 11, background: "var(--nav-bg)", padding: "2px 4px", borderRadius: 4 }}>{String(value)}</code>;
    default: return <span>{String(value)}</span>;
  }
}

// ─── DetailTabRenderer ────────────────────────────────────────────────────────

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
  return (
    <pre style={{ margin: 0, padding: 16, background: "var(--nav-bg)", overflow: "auto" }}>
      <code>{JSON.stringify(data[tab.field] || data, null, 2)}</code>
    </pre>
  );
}

// ─── Main BoardPage ───────────────────────────────────────────────────────────

export default function BoardPage() {
  const config = useConfig();
  const tabs = config.board.tabs;
  const [activeDir, setActiveDir] = useState(tabs[0]?.dir ?? "");
  const [items, setItems] = useState<JsonRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Inline expansion
  const [expandedRowKey, setExpandedRowKey] = useState<string | null>(null);
  const [expandedRecord, setExpandedRecord] = useState<JsonRecord | null>(null);

  // Raw JSON drawer
  const [rawDrawer, setRawDrawer] = useState<{ title: string; data: unknown } | null>(null);

  // Per-source refresh
  const [refreshingSource, setRefreshingSource] = useState<string | null>(null);

  const boardRefreshDirs = useAppStore((s) => s.boardRefreshDirs);
  const consumeBoardRefresh = useAppStore((s) => s.consumeBoardRefresh);
  const injectChatMessage = useAppStore((s) => s.injectChatMessage);

  const PAGE_SIZE = 20;

  const fetchList = useCallback(
    async (dir: string, p: number, source?: BoardTabSource) => {
      setLoading(true);
      try {
        if (source && source.provider === "rest" && source.endpoints?.list) {
          const res = await api.getBoardListCustom(source.endpoints.list, { page: p, page_size: PAGE_SIZE });
          const mapping = source.list_response ?? {};
          setItems((res as Record<string, unknown>)[mapping.items ?? "items"] as JsonRecord[] ?? []);
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
    setExpandedRowKey(null);
    setExpandedRecord(null);
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
    const aVal = a[sortKey], bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return sortOrder === "asc" ? -1 : 1;
    if (bVal == null) return sortOrder === "asc" ? 1 : -1;
    const cmp = typeof aVal === "number" && typeof bVal === "number"
      ? aVal - bVal
      : String(aVal).localeCompare(String(bVal));
    return sortOrder === "asc" ? cmp : -cmp;
  });

  const getRowKey = (record: JsonRecord, i: number): string => {
    const tab = tabs.find((t) => t.dir === activeDir);
    return tab?.source ? String(record[tab.source.id_field] ?? i) : record._filename;
  };

  const handleRowToggle = (record: JsonRecord, rowKey: string) => {
    if (expandedRowKey === rowKey) {
      setExpandedRowKey(null);
      setExpandedRecord(null);
    } else {
      setExpandedRowKey(rowKey);
      setExpandedRecord(record);
    }
  };

  const handleRefreshSource = async (matchId: string, source: string) => {
    setRefreshingSource(source);
    try {
      const result = await api.refreshMatchSource(matchId, source);
      if (expandedRecord) {
        const updated = {
          ...expandedRecord,
          raw_data: {
            ...(expandedRecord.raw_data as Record<string, unknown> ?? {}),
            [source]: result.data,
          },
        };
        setExpandedRecord(updated);
        // Also update items array so the data persists after collapse/re-expand
        setItems((prev) => prev.map((item) =>
          (item.match_id === matchId ? updated : item) as JsonRecord
        ));
      }
      message.success(`${source} 数据已更新`);
    } catch (e) {
      message.error(`获取失败: ${e instanceof Error ? e.message : "未知错误"}`);
    } finally {
      setRefreshingSource(null);
    }
  };

  const handleViewRaw = (title: string, data: unknown) => {
    setRawDrawer({ title, data });
  };

  const handleInjectChat = (record: JsonRecord) => {
    const tab = tabs.find((t) => t.dir === activeDir);
    if (tab?.source) {
      const idValue = String(record[tab.source.id_field] ?? "unknown");
      injectChatMessage(`请解读以下数据（${idValue}）：\n\n${JSON.stringify(record, null, 2)}`);
    } else {
      const { _filename, ...rest } = record;
      injectChatMessage(`请解读以下数据（${_filename}）：\n\n${JSON.stringify(rest, null, 2)}`);
    }
  };

  const activeTab = tabs.find((t) => t.dir === activeDir);
  const colCount = activeTab?.columns.length ?? 1;

  // Detect whether inline panel should use match-specific layout
  const isMatchRecord = (record: JsonRecord) =>
    typeof record.match_id === "string" && typeof record.raw_data === "object";

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
                  return (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      style={{
                        padding: "8px 16px", textAlign: "left",
                        fontSize: 11, fontWeight: 600,
                        color: isSorted ? "var(--accent)" : "var(--text-muted)",
                        textTransform: "uppercase", letterSpacing: "0.06em",
                        borderBottom: "1px solid var(--border)",
                        cursor: "pointer", userSelect: "none",
                      }}
                    >
                      {col.label}{isSorted ? (sortOrder === "asc" ? " ↑" : " ↓") : ""}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((record, i) => {
                const rowKey = getRowKey(record, i);
                const isExpanded = expandedRowKey === rowKey;

                return (
                  <Fragment key={rowKey}>
                    {/* Data row */}
                    <tr
                      style={{
                        borderBottom: isExpanded ? "none" : "1px solid var(--border-subtle)",
                        background: isExpanded ? "color-mix(in srgb, var(--nav-bg) 40%, transparent)" : "transparent",
                        cursor: "pointer",
                      }}
                      onClick={() => handleRowToggle(record, rowKey)}
                      onMouseEnter={(e) => {
                        if (!isExpanded) (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isExpanded) (e.currentTarget as HTMLElement).style.background = "transparent";
                      }}
                    >
                      {activeTab?.columns.map((col, colIdx) => (
                        <td key={col.key} style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>
                          {colIdx === 0 ? (
                            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ color: "var(--text-muted)", fontSize: 10, flexShrink: 0 }}>
                                {isExpanded ? <DownOutlined /> : <RightOutlined />}
                              </span>
                              <span style={{ color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                                <CellRenderer col={col} value={record[col.key]} />
                              </span>
                            </span>
                          ) : (
                            <CellRenderer col={col} value={record[col.key]} />
                          )}
                        </td>
                      ))}
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={colCount} style={{ padding: 0, borderBottom: "1px solid var(--border)" }}>
                          {expandedRecord && isMatchRecord(expandedRecord) ? (
                            <MatchDataPanel
                              record={expandedRecord}
                              onViewRaw={handleViewRaw}
                              onRefresh={handleRefreshSource}
                              refreshingSource={refreshingSource}
                            />
                          ) : expandedRecord ? (
                            (() => {
                              if (activeTab?.source?.detail.mode === "tabs" && activeTab.source.detail.tabs?.length) {
                                return (
                                  <div style={{ padding: "8px 16px" }}>
                                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginBottom: 8 }}>
                                      <Button size="small" onClick={() => handleInjectChat(expandedRecord)}>助手解读</Button>
                                    </div>
                                    <Tabs
                                      size="small"
                                      items={activeTab.source.detail.tabs!.map((dt) => ({
                                        key: dt.label,
                                        label: dt.label,
                                        children: <DetailTabRenderer tab={dt} data={expandedRecord} />,
                                      }))}
                                    />
                                  </div>
                                );
                              }
                              return (
                                <div style={{ padding: 16 }}>
                                  <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginBottom: 8 }}>
                                    <Button size="small" onClick={() => handleViewRaw("原始数据", expandedRecord)}>查看原始数据</Button>
                                    <Button size="small" type="primary" onClick={() => handleInjectChat(expandedRecord)}>助手解读</Button>
                                  </div>
                                  <pre style={{
                                    background: "#0a0a12", color: "var(--green)",
                                    padding: 12, borderRadius: 6, fontSize: 12,
                                    overflowX: "auto", whiteSpace: "pre-wrap",
                                    border: "1px solid var(--border)", maxHeight: 300, overflow: "auto",
                                  }}>
                                    {JSON.stringify(
                                      Object.fromEntries(Object.entries(expandedRecord).filter(([k]) => k !== "_filename")),
                                      null, 2,
                                    )}
                                  </pre>
                                </div>
                              );
                            })()
                          ) : null}
                        </td>
                      </tr>
                    )}
                  </Fragment>
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

      {/* Raw JSON Drawer */}
      <Drawer
        title={rawDrawer?.title ?? "原始数据"}
        placement="right"
        width={580}
        onClose={() => setRawDrawer(null)}
        open={!!rawDrawer}
      >
        <pre style={{
          background: "#0a0a12", color: "var(--green)",
          padding: 16, borderRadius: 8, fontSize: 12,
          overflowX: "auto", whiteSpace: "pre-wrap",
          border: "1px solid var(--border)",
        }}>
          {rawDrawer ? JSON.stringify(rawDrawer.data, null, 2) : ""}
        </pre>
      </Drawer>
    </div>
  );
}
