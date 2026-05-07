"""
在 Liverpool vs Chelsea (365992561) 附近扫 ID，找 Chelsea vs Nottm Forest。
验证 OddAlerts 是否有历史比赛的赔率。
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from provider.oddalerts.client import OddAlertsProvider
    p = OddAlertsProvider()

    # Liverpool vs Chelsea = 365992561 (May 9, 未来)
    # Chelsea vs Nottm Forest = May 4 (更早，ID 应该更小)
    # 在 365980000 ~ 365992561 范围内扫，找 Chelsea 相关
    print("扫描 ID 范围 365980000 ~ 365995000，寻找 Chelsea 相关比赛...")

    base = 365992561
    # 先试几个固定步长
    found = []
    # 顺序不重要，批量并发
    step = 200
    start = base - 15000
    end = base + 2000

    async def check(fid):
        fx = await p.get_fixture(fid)
        if isinstance(fx, dict) and fx.get("id"):
            home = fx.get("home_name", "")
            away = fx.get("away_name", "")
            status = fx.get("status", "")
            date = fx.get("date", "")[:10]
            return (fid, home, away, status, date)
        return None

    # 并发批次
    semaphore = asyncio.Semaphore(10)
    async def safe_check(fid):
        async with semaphore:
            return await check(fid)

    ids = list(range(start, end, 50))  # 步长 50，共约 340 次请求
    print(f"测试 {len(ids)} 个 ID...")

    results = await asyncio.gather(*[safe_check(i) for i in ids])

    epl_results = [r for r in results if r and r[1]]  # 过滤有数据的

    print(f"\n找到 {len(epl_results)} 个有效 fixture:")
    for r in epl_results:
        fid, home, away, status, date = r
        marker = " ← Chelsea!" if "chelsea" in home.lower() or "chelsea" in away.lower() else ""
        print(f"  {fid}: {home} vs {away} ({status}, {date}){marker}")

    # 如果找到 Chelsea vs Nottm Forest，验证历史赔率
    chelsea_nottm = [(r[0], r[1], r[2]) for r in epl_results
                     if r and ("nottingham" in r[1].lower() or "nottingham" in r[2].lower())]
    if chelsea_nottm:
        print(f"\n✅ 找到 Chelsea vs Nottm Forest!")
        for fid, home, away in chelsea_nottm:
            odds = await p.get_odds_history(fid)
            if isinstance(odds, dict):
                count = len(odds.get("data", []))
                print(f"  odds_history 条数: {count}（历史赔率{'存在' if count > 0 else '为空'}）")
    else:
        print("\n这个 ID 范围内未找到目标比赛，可能需要扩大扫描范围")
        # 看 EPL 比赛的 ID 分布规律
        epl_matches = [r for r in epl_results if r and r[3] in ("NS", "FT", "LIVE")]
        if epl_matches:
            print("已找到的比赛中 ID 规律:")
            for r in epl_matches[:5]:
                print(f"  {r[0]}: {r[1]} vs {r[2]} ({r[4]})")

    await p.close()

asyncio.run(main())
