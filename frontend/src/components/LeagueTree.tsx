import { useMemo, useState } from "react";
import { Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { Competition } from "../types/browse";

interface Props {
  competitions: Competition[];
  selectedId?: number;
  onSelect: (competitionId: number | undefined) => void;
}

export default function LeagueTree({ competitions, selectedId, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const grouped: Record<string, Competition[]> = {};
    for (const c of competitions) {
      if (q && !`${c.name} ${c.country ?? ""}`.toLowerCase().includes(q)) continue;
      const key = c.country || "其他";
      (grouped[key] ||= []).push(c);
    }
    return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));
  }, [competitions, query]);

  return (
    <div className="league-tree">
      <Input
        prefix={<SearchOutlined />}
        placeholder="搜索联赛 / 国家"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        size="small"
      />
      <div className="league-tree-shortcut">
        <div className={`shortcut ${selectedId === undefined ? "on" : ""}`}
             onClick={() => onSelect(undefined)}>📅 今日比赛</div>
      </div>
      {groups.map(([country, items]) => (
        <div key={country} className="league-tree-group">
          <div className="league-tree-country">{country}</div>
          {items.map((c) => (
            <div key={c.id}
                 className={`league-tree-item ${selectedId === c.id ? "on" : ""}`}
                 onClick={() => onSelect(c.id)}>
              {c.name}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
