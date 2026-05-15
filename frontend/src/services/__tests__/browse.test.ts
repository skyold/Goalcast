import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { browseApi } from "../browse";

beforeEach(() => { globalThis.fetch = vi.fn() as unknown as typeof fetch; });
afterEach(() => vi.restoreAllMocks());

describe("browseApi", () => {
  it("getCompetitions returns parsed list", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true, json: async () => [{ id: 8, name: "Premier League", country: "England" }],
    });
    const out = await browseApi.getCompetitions();
    expect(out[0].name).toBe("Premier League");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/competitions", expect.any(Object));
  });

  it("getFixtures forwards date and competition_id", async () => {
    (globalThis.fetch as any).mockResolvedValue({ ok: true, json: async () => [] });
    await browseApi.getFixtures({ date: "2026-05-14", competitionId: 8 });
    const url = (globalThis.fetch as any).mock.calls[0][0];
    expect(url).toBe("/api/fixtures?date=2026-05-14&competition_id=8");
  });

  it("getFixtureDetail returns 404 as null", async () => {
    (globalThis.fetch as any).mockResolvedValue({ ok: false, status: 404, text: async () => "nf" });
    const out = await browseApi.getFixtureDetail(999);
    expect(out).toBeNull();
  });

  it("runAnalysis posts", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true, json: async () => ({ run_id: "0099", status: "started" })
    });
    const out = await browseApi.runAnalysis();
    expect(out.run_id).toBe("0099");
    expect((globalThis.fetch as any).mock.calls[0][1].method).toBe("POST");
  });
});
