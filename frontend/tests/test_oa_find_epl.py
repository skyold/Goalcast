"""
找 Chelsea vs Nottingham Forest (5月4日) 的 OA fixture ID。
已知 Liverpool vs Chelsea (5月9日) = 365992561，两场都在同一赛季，
OA ID 应该在相近范围。
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from provider.oddalerts.client import OddAlertsProvider
    p = OddAlertsProvider()

    # 1. 验证 Liverpool vs Chelsea 这个 ID
    fx = await p.get_fixture(365992561)
    print(f"Liverpool vs Chelsea fixture: {fx}")
    print()

    # 2. 试试 fixtures/between 端点，传入 5月4日
    import httpx, json
    from config.settings import settings
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        # 试不同的日期格式
        for fmt in [
            {"from": "2026-05-04", "to": "2026-05-04"},
            {"from": "2026-05-03", "to": "2026-05-05"},
            {"date": "2026-05-04"},
        ]:
            params = {"api_token": settings.ODDALERTS_API_KEY, **fmt}
            r = await client.get("https://data.oddalerts.com/api/fixtures/between", params=params)
            print(f"fixtures/between {fmt} → {r.status_code}")
            try:
                data = r.json()
                items = data.get("data", [])
                total = data.get("total", "?")
                print(f"  total={total}, items={len(items)}")
                # 找 Chelsea
                for it in items[:5]:
                    print(f"  {it}")
                if items:
                    break
            except Exception as e:
                print(f"  JSON parse error: {e}, body={r.text[:100]}")
        print()

    # 3. 在 dropping odds 里搜索更多页，看是否有已结束的比赛（unix < now）
    import time
    now = time.time()
    print(f"=== 扫描 dropping odds 所有页找 Chelsea vs Nottm Forest ===")
    for page in range(1, 120):  # 29685条/250条每页 ≈ 119页
        resp = await p.get_dropping_odds(page=page)
        if not isinstance(resp, dict):
            break
        items = resp.get("data", [])
        if not items:
            break
        for it in items:
            name = it.get("fixture_name", "")
            if "chelsea" in name.lower() and "nottingham" in name.lower():
                print(f"  page={page} ✅ {name}, id={it.get('fixture_id')}, unix={it.get('unix')}")
            # 一旦所有 items 的 unix 都在未来，停止扫描
        # 打印进度
        if page % 20 == 0:
            min_unix = min((it.get("unix", 0) for it in items), default=0)
            max_unix = max((it.get("unix", 0) for it in items), default=0)
            import datetime
            print(f"  page {page}: unix range {datetime.datetime.fromtimestamp(min_unix).strftime('%m-%d')} ~ {datetime.datetime.fromtimestamp(max_unix).strftime('%m-%d')}")

    await p.close()

asyncio.run(main())
