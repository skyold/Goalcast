"""
验证 OddAlerts 是否有历史比赛数据。

思路：
1. 从 trends 里找一场已知的 OA fixture ID（未来比赛）→ 等它结束后再查，看 odds_history 是否还在
2. 更直接：找一场 OA 知道的「昨天/前天」比赛，看赔率记录是否存在
3. 用 dropping odds 的分页数据找「已结束状态」的比赛（status=FT）
"""
import asyncio, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from provider.oddalerts.client import OddAlertsProvider
    p = OddAlertsProvider()

    # ── 1. 检查 dropping odds 里是否有已结束(FT)的比赛 ─────────────────────
    print("=== 扫描 dropping odds，找已结束的比赛 ===")
    finished = []
    for page in range(1, 4):
        resp = await p.get_dropping_odds(page=page)
        if not isinstance(resp, dict):
            break
        for it in resp.get("data", []):
            # dropping odds 本身没有 status 字段，只有 unix 时间
            # 如果 unix < now → 已开赛/结束
            import time
            unix = it.get("unix", 0)
            if unix and unix < time.time():
                fid = it.get("fixture_id")
                name = it.get("fixture_name", "")
                comp = it.get("competition_name", "")
                if fid and (fid, name) not in [(f["fid"], f["name"]) for f in finished]:
                    finished.append({"fid": fid, "name": name, "comp": comp, "unix": unix})
        if len(finished) >= 5:
            break

    if finished:
        print(f"找到 {len(finished)} 场已开赛/结束的比赛：")
        for f in finished[:5]:
            import datetime
            dt = datetime.datetime.fromtimestamp(f['unix']).strftime('%m-%d %H:%M')
            print(f"  {f['comp']}: {f['name']} (ko={dt}, oa_id={f['fid']})")
    else:
        print("dropping odds 里没有已结束的比赛（说明该端点只含未来赛事）")

    print()

    # ── 2. 直接用一个已知的 OA fixture ID 查 odds_history ──────────────────
    # 从映射表里取一个已找到的 OA ID
    map_file = Path(__file__).parent / "data" / "oddalerts_fixture_map.json"
    known_oa_id = None
    if map_file.exists():
        cache = json.loads(map_file.read_text())
        # 取第一个非 None 的值
        for v in cache.values():
            if v is not None:
                known_oa_id = v
                break

    if known_oa_id:
        print(f"=== 验证已知 OA fixture_id={known_oa_id} 的数据完整性 ===")
        fixture = await p.get_fixture(known_oa_id)
        if isinstance(fixture, dict):
            status = fixture.get("status", "?")
            home = fixture.get("home_name", "?")
            away = fixture.get("away_name", "?")
            print(f"  fixture: {home} vs {away}, status={status}")
        odds = await p.get_odds_history(known_oa_id)
        if isinstance(odds, dict):
            print(f"  odds_history 条数: {len(odds.get('data', []))}")
        stats = await p.get_stats("fixture", known_oa_id)
        if isinstance(stats, dict):
            print(f"  stats 条数: {len(stats.get('data', []))}")
    print()

    # ── 3. 直接尝试用 fixtures/id 查 Chelsea vs Nottm Forest 可能的 OA ID ───
    # 尝试在 trends 多页里搜索 Chelsea
    print("=== 在 trends 搜索 Chelsea ===")
    found_chelsea = False
    for market in ("homeWin", "awayWin", "btts"):
        for page in range(1, 10):
            resp = await p.get_trends(market, page=page)
            if not isinstance(resp, dict):
                break
            items = resp.get("data", [])
            if not items:
                break
            for it in items:
                home = it.get("home_name", "")
                away = it.get("away_name", "")
                if "chelsea" in home.lower() or "chelsea" in away.lower():
                    print(f"  [{market} p{page}] id={it.get('id')} {home} vs {away} ko={it.get('ko_time')}")
                    found_chelsea = True
        if found_chelsea:
            break
    if not found_chelsea:
        print("  trends 里没有找到 Chelsea（说明 EPL 当前无未来赛程在 OA 的 trends 里）")

    print()

    # ── 4. 直接尝试 Chelsea vs Nottm Forest (19427210) 用不同的 ID 格式 ──────
    print("=== 尝试直接查 Chelsea vs Nottm Forest（各种 ID 猜测） ===")
    # 用 OA 的格式试试，OA ID 比较大，试试 SM ID 在 OA 的某个范围
    test_ids = [
        19427210,     # 直接 SM ID
        420427210,    # 加 4 亿前缀（观察 OA ID 规律）
        421427210,
    ]
    for tid in test_ids:
        fx = await p.get_fixture(tid)
        if isinstance(fx, dict) and fx.get("id"):
            print(f"  ✅ ID {tid}: {fx.get('home_name')} vs {fx.get('away_name')} status={fx.get('status')}")
        else:
            print(f"  ❌ ID {tid}: 无数据 (返回={type(fx).__name__}: {str(fx)[:60]})")

    await p.close()

asyncio.run(main())
