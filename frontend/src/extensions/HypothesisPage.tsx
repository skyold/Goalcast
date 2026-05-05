import type { CSSProperties } from "react";
import { useState } from "react";
import { message } from "antd";
import { extApi } from "../services/extensions";
import type { HypothesisFormData } from "../types/extensions";

const EXAMPLE_HYPOTHESES = [
  "When funding rate reaches extreme negative values (< -0.05%), BTC/USDT tends to mean-revert on 1h timeframe with ~65% win rate",
  "High volume divergence from price action on 4h candles signals potential trend reversal in top-20 altcoins",
  "Order book imbalance ratio > 3 at key support levels predicts short-term price recovery in BTC",
];

const THEMES = [
  { value: "",              label: "Any Theme"     },
  { value: "funding_rate",  label: "Funding Rate"  },
  { value: "volatility",    label: "Volatility"    },
  { value: "momentum",      label: "Momentum"      },
  { value: "volume",        label: "Volume"        },
  { value: "mean_reversion",label: "Mean Reversion"},
];

const inputBase: CSSProperties = {
  width: "100%",
  background: "var(--card-bg)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--text-primary)",
  fontSize: 13,
  fontFamily: "inherit",
  outline: "none",
  transition: "border-color 0.15s",
  boxSizing: "border-box",
};

export default function HypothesisPage() {
  const [form, setForm]       = useState<HypothesisFormData>({ hypothesis: "", mode: "semi", theme: null });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const charCount = form.hypothesis.length;
  const MAX_CHARS = 600;

  const handleSubmit = async () => {
    if (!form.hypothesis.trim()) return;
    setLoading(true);
    try {
      const res = await extApi.submitHypothesis(form);
      setSubmitted(res.hypothesis_id);
      setForm({ hypothesis: "", mode: "semi", theme: null });
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Success banner */}
      {submitted && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 10, background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.25)" }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2.5">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--green)" }}>Hypothesis submitted successfully</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, fontFamily: "var(--font-mono)" }}>
              {submitted} — queued for R&amp;D Pipeline
            </div>
          </div>
          <button onClick={() => setSubmitted(null)} style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 16 }}>×</button>
        </div>
      )}

      {/* Form card */}
      <div style={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
        {/* Header */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", background: "var(--nav-bg)", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--accent-bg)", border: "1px solid var(--accent-border)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)" }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>New Research Hypothesis</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>Queued for Strategist → Miner → Judge → Scribe pipeline</div>
          </div>
        </div>

        <div style={{ padding: 20 }}>
          {/* Hypothesis textarea */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Research Hypothesis *</label>
              <span style={{ fontSize: 11, color: charCount > MAX_CHARS ? "#ef4444" : "var(--text-muted)" }}>
                {charCount} / {MAX_CHARS}
              </span>
            </div>
            <textarea
              value={form.hypothesis}
              onChange={(e) => setForm((f) => ({ ...f, hypothesis: e.target.value }))}
              onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
              onBlur={(e)  => (e.target.style.borderColor = "var(--border)")}
              rows={6}
              placeholder={`Describe your hypothesis clearly with:\n• Asset(s) and timeframe\n• Expected market behavior\n• Conditions or triggers`}
              style={{ ...inputBase, padding: "12px 14px", resize: "vertical", lineHeight: 1.6 }}
            />
          </div>

          {/* Mode + Theme */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
            {/* Mode segmented */}
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
                Execution Mode
              </label>
              <div style={{ display: "flex", background: "var(--nav-bg)", borderRadius: 8, border: "1px solid var(--border)", padding: 3 }}>
                {([
                  { value: "semi", label: "SEMI", desc: "confirm at checkpoints" },
                  { value: "full", label: "FULL", desc: "fully autonomous"       },
                ] as const).map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setForm((f) => ({ ...f, mode: opt.value }))}
                    style={{
                      flex: 1, padding: "7px 10px", borderRadius: 6, border: "none", cursor: "pointer",
                      fontFamily: "inherit", fontWeight: 600, fontSize: 12,
                      background: form.mode === opt.value ? "var(--accent)" : "transparent",
                      color:      form.mode === opt.value ? "#000" : "var(--text-muted)",
                      transition: "all 0.15s",
                    }}
                  >
                    {opt.label}
                    <div style={{ fontSize: 10, fontWeight: 400, marginTop: 1, opacity: 0.7 }}>{opt.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Theme select */}
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
                Theme (optional)
              </label>
              <select
                value={form.theme ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, theme: e.target.value || null }))}
                onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
                onBlur={(e)  => (e.target.style.borderColor = "var(--border)")}
                style={{ ...inputBase, padding: "10px 12px" }}
              >
                {THEMES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>

          {/* Submit + Draft */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleSubmit}
              disabled={loading || !form.hypothesis.trim()}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: 8, border: "none", cursor: loading ? "not-allowed" : "pointer",
                fontFamily: "inherit", fontSize: 13, fontWeight: 600,
                background: "var(--accent)", color: "#000",
                boxShadow: "0 0 16px var(--accent-glow)",
                opacity: loading || !form.hypothesis.trim() ? 0.6 : 1,
                transition: "opacity 0.15s",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor"/>
              </svg>
              {loading ? "Submitting…" : "Submit & Execute"}
            </button>
            <button
              onClick={() => message.info("Draft saved (local only)")}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 500, background: "var(--card-bg)", color: "var(--text-secondary)" }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
              </svg>
              Save Draft
            </button>
          </div>
        </div>
      </div>

      {/* Pipeline info */}
      <div style={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "16px 20px" }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>Execution Pipeline</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[
            { name: "Strategist", desc: "Refines & structures the hypothesis",    color: "#60a5fa" },
            { name: "Miner",      desc: "Writes & backtests alpha factor code",   color: "var(--accent)" },
            { name: "Judge",      desc: "Evaluates IC/IR and approves factors",   color: "#a855f7" },
            { name: "Scribe",     desc: "Documents & commits to knowledge base",  color: "var(--green)" },
          ].map((step, i) => (
            <div key={step.name} style={{ background: "var(--nav-bg)", borderRadius: 8, padding: "10px 12px", border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                <div style={{ width: 20, height: 20, borderRadius: "50%", background: `${step.color}22`, border: `1px solid ${step.color}44`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: step.color }}>{i + 1}</div>
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{step.name}</span>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Example hypotheses */}
      <div style={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "16px 20px" }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>Example Hypotheses</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {EXAMPLE_HYPOTHESES.map((ex, i) => (
            <div
              key={i}
              onClick={() => setForm((f) => ({ ...f, hypothesis: ex }))}
              style={{ padding: "10px 14px", borderRadius: 8, cursor: "pointer", background: "var(--nav-bg)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, transition: "all 0.15s" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--accent-border)"; (e.currentTarget as HTMLElement).style.background = "var(--accent-bg)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";        (e.currentTarget as HTMLElement).style.background = "var(--nav-bg)"; }}
            >
              <span style={{ color: "var(--accent)", marginRight: 8, fontSize: 10 }}>USE →</span>
              {ex}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
