"""精准查找 Chelsea vs Nottm Forest，验证历史赔率可访问性。"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from provider.oddalerts.client import OddAlertsProvider
    p = OddAlertsProvider()

    # 两个 track 各扫下一段：track A = 650,700,750... track B = 661,711,761...
    # 再往大扫到 366000000
    track_a = list(range(365992650, 366000001, 50))
    track_b = list(range(365992661, 366000001, 50))
    ids = sorted(set(track_a + track_b))
    print(f"扫描 {len(ids)} 个 ID（EPL 双 track）...\n")

    semaphore = asyncio.Semaphore(20)
    async def check(fid):
        async with semaphore:
            fx = await p.get_fixture(fid)
            if isinstance(fx, dict) and fx.get("id"):
                return {"id": fid, "home": fx.get("home_name",""), "away": fx.get("away_name",""),
                        "status": fx.get("status",""), "date": (fx.get("date","") or "")[:10]}
            return None

    results = await asyncio.gather(*[check(i) for i in ids])
    matches = [r for r in results if r]
    print(f"找到 {len(matches)} 个比赛:\n")

    target = None
    for m in sorted(matches, key=lambda x: x["date"]):
        h, a = m["home"], m["away"]
        is_target = (
            ("chelsea" in h.lower() and "nottingham" in a.lower()) or
            ("nottingham" in h.lower() and "chelsea" in a.lower())
        )
        tag = " *** 目标！" if is_target else ""
        print(f"  {m['id']}: {h} vs {a} ({m['status']}, {m['date']}){tag}")
        if is_target:
            target = m

    if target:
        print(f"\n✅ 找到！oa_fixture_id={target['id']}")
        odds = await p.get_odds_history(target["id"])
        if isinstance(odds, dict):
            data = odds.get("data", [])
            print(f"  odds_history 记录数: {len(data)}")
            if data:
                markets = sorted({d.get("market_key") for d in data})
                print(f"  市场类型: {markets}")
                ft = [d for d in data if d.get("market_key") == "ft_result"]
                if ft:
                    sample = ft[0]
                    print(f"  ft_result 示例 ({sample.get('bookmaker_name')}): "
                          f"opening={sample.get('opening')} closing={sample.get('closing')}")
        stats = await p.get_stats("fixture", target["id"])
        if isinstance(stats, dict):
            rows = stats.get("data", [])
            print(f"  stats 记录数: {len(rows)}")
            if rows:
                for row in rows:
                    print(f"    {row.get('name')}: xg_for={row.get('xg_for')}, xg_against={row.get('xg_against')}")
    else:
        print("\n❌ 这两个 track 里也没找到，结论见下方")

    await p.close()

asyncio.run(main())
