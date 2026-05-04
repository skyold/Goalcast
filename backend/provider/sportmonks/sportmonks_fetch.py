"""
SportMonks v3 数据提取脚本
提取字段：1X2 / BTTS / O/U 2.5 / 正确比分 / xG
筛选方式：日期 + 联赛ID（可选）
"""

import requests
import json
from datetime import date, timedelta

# ─────────────────────────────────────────
# 配置区：填入你的API KEY和筛选条件
# ─────────────────────────────────────────
API_TOKEN = "YOUR_API_TOKEN_HERE"   # ← 填入你的SportMonks API key

# 日期范围（默认取明天的比赛）
DATE_FROM = str(date.today() + timedelta(days=1))   # 格式 YYYY-MM-DD
DATE_TO   = str(date.today() + timedelta(days=1))   # 同一天就设成一样

# 联赛筛选（留空 [] 则拉取所有联赛）
# 常用联赛ID参考：
#   EPL=8  La Liga=564  Serie A=384  Bundesliga=82  Ligue 1=301
#   J-League=271  K-League=1036  CSL=720  A-League=650
LEAGUE_IDS = []   # 例如 [271, 1036] 只看J联赛和K联赛

BASE_URL = "https://api.sportmonks.com/v3/football"

# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────
def get(endpoint, params={}):
    params["api_token"] = API_TOKEN
    r = requests.get(f"{BASE_URL}{endpoint}", params=params)
    if r.status_code != 200:
        print(f"  ❌ API错误 {r.status_code}: {endpoint}")
        return None
    return r.json()

def parse_predictions(predictions_list):
    """从predictions数组提取各市场概率"""
    result = {
        "home": None, "draw": None, "away": None,
        "btts_yes": None, "btts_no": None,
        "over_2_5": None, "under_2_5": None,
        "correct_score": None
    }
    for p in predictions_list:
        preds = p.get("predictions", {})
        type_code = p.get("type", {}).get("code", "") or p.get("type", {}).get("developer_name", "")

        if "3way" in type_code.lower() or p.get("type_id") in [1, 52]:
            result["home"] = preds.get("home")
            result["draw"] = preds.get("draw")
            result["away"] = preds.get("away")
        elif "btts" in type_code.lower() or p.get("type_id") == 179:
            result["btts_yes"] = preds.get("yes")
            result["btts_no"]  = preds.get("no")
        elif "over-under-2_5" in type_code.lower() or p.get("type_id") == 235:
            result["over_2_5"]  = preds.get("yes")
            result["under_2_5"] = preds.get("no")
        elif "correct_score" in type_code.lower() or "correct-score" in type_code.lower():
            result["correct_score"] = preds

    # 兜底：直接从data字段读（旧版格式）
    if result["home"] is None and isinstance(predictions_list, dict):
        p = predictions_list
        result["home"]       = p.get("home")
        result["draw"]       = p.get("draw")
        result["away"]       = p.get("away")
        result["btts_yes"]   = p.get("btts")
        result["over_2_5"]   = p.get("over_2_5")
        result["under_2_5"]  = p.get("under_2_5")
        result["correct_score"] = p.get("correct_score")

    return result

def parse_xg(xg_list):
    """从xG数组提取主客队xG"""
    home_xg, away_xg = None, None
    for item in xg_list:
        participant = item.get("participant", "")
        val = item.get("data", {}).get("value") or item.get("value")
        name = item.get("type", {}).get("name", "")
        if "Expected Goals" in name and "on Target" not in name:
            if participant == "home" or item.get("location") == "home":
                home_xg = val
            elif participant == "away" or item.get("location") == "away":
                away_xg = val
    return home_xg, away_xg

# ─────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────
def fetch_fixtures():
    print(f"\n📅 拉取比赛：{DATE_FROM} → {DATE_TO}")
    if LEAGUE_IDS:
        print(f"🏆 联赛筛选：{LEAGUE_IDS}")

    # Step 1: 拉取日期内所有比赛（含predictions和participants）
    params = {
        "include": "predictions;participants;xGFixture",
    }
    if LEAGUE_IDS:
        params["filters"] = "fixtureLeagues:" + ",".join(str(i) for i in LEAGUE_IDS)

    data = get(f"/fixtures/between/{DATE_FROM}/{DATE_TO}", params)
    if not data or "data" not in data:
        print("❌ 无法获取比赛数据，请检查API key或日期范围")
        return []

    fixtures = data["data"]
    print(f"✅ 找到 {len(fixtures)} 场比赛\n")

    results = []
    for fx in fixtures:
        fixture_id   = fx.get("id")
        fixture_name = fx.get("name", "未知比赛")
        starting_at  = fx.get("starting_at", "")
        league_id    = fx.get("league_id")

        # 主客队名称
        home_name, away_name = "主队", "客队"
        for p in fx.get("participants", []):
            meta = p.get("meta", {})
            if meta.get("location") == "home":
                home_name = p.get("name", "主队")
            elif meta.get("location") == "away":
                away_name = p.get("name", "客队")

        # 解析预测概率
        raw_preds = fx.get("predictions", [])
        if isinstance(raw_preds, dict) and "data" in raw_preds:
            raw_preds = raw_preds["data"]
        probs = parse_predictions(raw_preds if isinstance(raw_preds, list) else [])

        # 解析xG
        raw_xg = fx.get("xgfixture", [])
        if isinstance(raw_xg, dict) and "data" in raw_xg:
            raw_xg = raw_xg["data"]
        home_xg, away_xg = parse_xg(raw_xg if isinstance(raw_xg, list) else [])

        # 如果fixture内没有predictions，单独请求
        if probs["home"] is None:
            print(f"  🔄 单独请求概率：{fixture_name}")
            p_data = get(f"/predictions/probabilities/fixtures/{fixture_id}")
            if p_data and "data" in p_data:
                raw = p_data["data"]
                if isinstance(raw, list):
                    probs = parse_predictions(raw)
                elif isinstance(raw, dict):
                    preds_inner = raw.get("predictions", raw)
                    probs = parse_predictions(preds_inner if isinstance(preds_inner, list) else preds_inner)

        entry = {
            "fixture_id":    fixture_id,
            "league_id":     league_id,
            "match":         fixture_name,
            "home":          home_name,
            "away":          away_name,
            "kickoff":       starting_at,
            "prob_home":     probs["home"],
            "prob_draw":     probs["draw"],
            "prob_away":     probs["away"],
            "btts_yes":      probs["btts_yes"],
            "btts_no":       probs["btts_no"],
            "over_2_5":      probs["over_2_5"],
            "under_2_5":     probs["under_2_5"],
            "correct_score": probs["correct_score"],
            "xg_home":       home_xg,
            "xg_away":       away_xg,
        }
        results.append(entry)

    return results

def print_results(results):
    print("=" * 72)
    print(f"{'比赛':<32} {'主胜%':>6} {'平%':>6} {'客胜%':>6} {'BTTS%':>6} {'大2.5%':>7} {'xG主':>6} {'xG客':>6}")
    print("=" * 72)
    for r in results:
        def f(v): return f"{v:.1f}" if v is not None else "  N/A"
        print(
            f"{r['match'][:31]:<32} "
            f"{f(r['prob_home']):>6} "
            f"{f(r['prob_draw']):>6} "
            f"{f(r['prob_away']):>6} "
            f"{f(r['btts_yes']):>6} "
            f"{f(r['over_2_5']):>7} "
            f"{f(r['xg_home']):>6} "
            f"{f(r['xg_away']):>6}"
        )
    print("=" * 72)

def save_json(results, filename="sportmonks_output.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 已保存至 {filename}")

# ─────────────────────────────────────────
# 运行
# ─────────────────────────────────────────
if __name__ == "__main__":
    results = fetch_fixtures()
    if results:
        print_results(results)
        save_json(results)
        print(f"\n✅ 完成，共 {len(results)} 场比赛")
    else:
        print("⚠️  没有找到符合条件的比赛")
