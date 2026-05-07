"""
以步长 50 扫描，找 Chelsea vs Nottingham Forest。
同时验证历史比赛的 odds_history 是否有实质数据。
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from provider.oddalerts.client import OddAlertsProvider
    p = OddAlertsProvider()

    # ID 步长 50，从 365990000 扫到 366010000
    ids = list(range(365990000, 366010001, 50))
    print(f"扫描 {len(ids)} 个 ID（步长50），寻找 Chelsea vs Nottm Forest...\n")

    semaphore = asyncio.Semaphore(15)

    async def check(fid):
        async with semaphore:
            fx = await p.get_fixture(fid)
            if isinstance(fx, dict) and fx.get("id"):
                return {
                    "id": fid,
                    "home": fx.get("home_name", ""),
                    "away": fx.get("away_name", ""),
                    "status": fx.get("status", ""),
                    "date": (fx.get("date", "") or "")[:10],
                    "comp": fx.get("competition_name", ""),
                }
            return None

    results = await asyncio.gather(*[check(i) for i in ids])
    matches = [r for r in results if r]

    print(f"找到 {len(matches)} 个有效比赛：\n")
    target = None
    for m in sorted(matches, key=lambda x: x["date"]):
        h, a = m["home"], m["away"]
        is_chelsea_nottm = (
            ("chelsea" in h.lower() and "nottingham" in a.lower()) or
            ("nottingham" in h.lower() and "chelsea" in a.lower())
        )
        if is_chelsea_nottm:
            print(f"  *** {m['id']}: {h} vs {a} ({m['status']}, {m['date']}) [{m['comp']}]")
            target = m
        else:
            print(f"  {m['id']}: {h} vs {a} ({m['status']}, {m['date']})")

    if target:
        print(f"\n✅ 找到目标！验证历史赔率...")
        odds = await p.get_odds_history(target["id"])
        if isinstance(odds, dict):
            data = odds.get("data", [])
            print(f"  odds_history 条数: {len(data)}")
            if data:
                markets = list({d.get("market_key") for d in data})
                print(f"  市场: {markets}")
                # 取 ft_result 开盘赔率示例
                ft = [d for d in data if d.get("market_key") == "ft_result"]
                if ft:
                    print(f"  ft_result 开盘赔率示例: {ft[0].get('opening')}")
        stats = await p.get_stats("fixture", target["id"])
        if isinstance(stats, dict):
            print(f"  stats 条数: {len(stats.get('data', []))}")
    else:
        print("\n这个 ID 范围内未找到 Chelsea vs Nottm Forest")
        print("找到的最近比赛（时间 ≥ 2026-05-01）:")
        for m in matches:
            if m["date"] >= "2026-05-01":
                print(f"  {m['id']}: {m['home']} vs {m['away']} ({m['date']})")

    await p.close()

asyncio.run(main())
