"""在 419-420M 范围找 May 4 的 Chelsea vs Nottm Forest。"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from provider.oddalerts.client import OddAlertsProvider
    p = OddAlertsProvider()

    # trends 里的 May 7-14 比赛在 420494291~420555946
    # May 4 的比赛应该在更低的 ID，试 419800000~420500000，步长 1000
    ids = list(range(419800000, 420500001, 500))
    print(f"扫描 {len(ids)} 个 ID（419.8M~420.5M，步长500）...\n")

    semaphore = asyncio.Semaphore(20)
    async def check(fid):
        async with semaphore:
            fx = await p.get_fixture(fid)
            if isinstance(fx, dict) and fx.get("id"):
                return {"id": fid, "home": fx.get("home_name",""), "away": fx.get("away_name",""),
                        "status": fx.get("status",""), "date": (fx.get("date","") or "")[:10],
                        "comp": fx.get("competition_name","")}
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
        print(f"  {m['id']}: {m['comp']} | {h} vs {a} ({m['status']}, {m['date']}){tag}")
        if is_target:
            target = m

    if target:
        print(f"\n✅ 找到！验证历史赔率...")
        odds = await p.get_odds_history(target["id"])
        if isinstance(odds, dict):
            data = odds.get("data", [])
            print(f"  odds_history 记录数: {len(data)}")
            if data:
                markets = sorted({d.get("market_key") for d in data})
                print(f"  市场: {markets}")
                ft = [d for d in data if d.get("market_key") == "ft_result"]
                if ft:
                    print(f"  ft_result 示例: {ft[0]}")
    else:
        print("\n这个范围也没找到目标比赛")
        # 打印找到的比赛时间分布，帮助理解 ID 规律
        if matches:
            dates = sorted(set(m["date"] for m in matches))
            print(f"找到的比赛日期范围: {dates[0]} ~ {dates[-1]}")

    await p.close()

asyncio.run(main())
