"""
OddAlerts 纯OA分析工具
数据：预测模型 vs 蒙特卡洛模拟对比 + H2H + 球队近期Scored/Conceded/xG + EV计算
结果保存到 oa_output.txt（同时显示在屏幕）
"""

import requests
import json
import math
import sys
from datetime import date, timedelta

# ─────────────────────────────────────────
API_TOKEN = "QV3tYqdMH9wkjY7uWIg2A37jq1wkml7FWPdaYGqpcfqbJ3it4jqWeyWTbY9a"   # ← 填入你的token
BASE_URL  = "https://data.oddalerts.com/api"

# 分歧门槛（模型 vs 模拟差距超过此值标记警告）
DIVERGENCE_THRESHOLD = 7.0
# ─────────────────────────────────────────

class Logger:
    def __init__(self, f):
        self.terminal = sys.stdout
        self.log = open(f, "w", encoding="utf-8")
    def write(self, m):
        self.terminal.write(m)
        self.log.write(m)
        self.log.flush()
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger("oa_output.txt")

def get(endpoint, params=None):
    if params is None: params = {}
    params["api_token"] = API_TOKEN
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=15)
        if r.status_code != 200: return None
        if not r.text.strip() or r.text.strip() == "OddAlerts Data Engine": return None
        return r.json()
    except Exception as e:
        print(f"  网络错误: {e}")
        return None

def sep(char="─", w=72): print(char * w)
def fmt(v, d=1): return f"{v:.{d}f}" if v is not None else "  —  "
def fmtp(v): return f"{v:.1f}%" if v is not None else "  —  "

# ─────────────────────────────────────────
# 显示比赛列表
# ─────────────────────────────────────────
def show_list(fixtures):
    # predictability 完整映射（覆盖所有OA可能的值）
    pred_map = {
        "great":   "great",
        "high":    "great",
        "good":    "good",
        "medium":  "good",    # OA部分联赛用medium
        "average": "avg",
        "low":     "poor",
        "poor":    "poor",
        None:      "--",
    }
    pred_stars = {
        "great": "★★★★",
        "good":  "★★★ ",
        "avg":   "★★  ",
        "poor":  "★   ",
        "--":    "    ",
    }
    sep("=")
    # 用固定宽度避免中文字符错位
    print(f"  {'#':>3}  {'比赛':<30} {'时间':>5}  {'联赛':<22}  {'可预测':>6}")
    sep()
    for i, fx in enumerate(fixtures):
        t        = fx["kickoff"][11:16] if len(fx["kickoff"]) > 10 else "--"
        pred_raw = fx.get("predictability")
        pred_lbl = pred_map.get(pred_raw, pred_raw or "--")
        stars    = pred_stars.get(pred_lbl, "    ")
        pred_str = f"{stars} {pred_lbl}" if pred_lbl != "--" else "  --"
        # 截断比赛名和联赛名防止错位
        match_str  = fx["match"][:28]
        league_str = fx["league"][:20]
        print(f"  {i+1:>3}  {match_str:<30} {t:>5}  {league_str:<22}  {pred_str}")
    sep()
    print("  可预测性: ★★★★great  ★★★good  ★★avg  ★poor  --无数据")
    sep("=")

# ─────────────────────────────────────────
# 拉取平博开盘赔率
# ─────────────────────────────────────────
def normalize_line(raw):
    """
    把OddAlerts让球值统一转成 (是否负数, 数字字符串)
    支持格式: 0, 05, 1, 125, -05, m05, m125, p05, p025
    m=minus(负), p=plus(正)
    """
    if raw is None: return False, "0"
    s = str(raw).strip()
    # 处理前缀
    if s.startswith("m"):
        neg = True
        digits = s[1:]
    elif s.startswith("-"):
        neg = True
        digits = s[1:]
    elif s.startswith("p"):
        neg = False
        digits = s[1:]
    else:
        neg = False
        digits = s
    # 转成小数字符串
    # OddAlerts格式：把小数点去掉，最后一位如果是5就是0.5的倍数
    # 05→0.5, 25→2.5, 1→1, 125→1.25（最后两位是25=.25）, 150→1.5
    if len(digits) == 1:
        val = digits                            # 0,1,2,3,4
    elif len(digits) == 2:
        if digits[1] == "0":
            val = digits[0]                     # 10→1, 20→2
        else:
            val = digits[0] + "." + digits[1]   # 05→0.5, 25→2.5, 15→1.5
    elif len(digits) == 3:
        # 125→1.25, 025→0.25, 075→0.75, 150→1.50→1.5
        if digits[2] == "0":
            # 150→1.5, 100→1.0→1
            inner = digits[0] + "." + digits[1]
            val = inner.rstrip("0").rstrip(".")
            if not val: val = "0"
        else:
            # 125→1.25, 025→0.25, 075→0.75
            val = digits[0] + "." + digits[1] + digits[2]
    else:
        val = digits
    return neg, val

def parse_line(raw):
    """把outcome让球值转成显示格式"""
    neg, val = normalize_line(raw)
    if val == "0": return "0"
    return ("-" if neg else "+") + val

def line_to_float(raw):
    """把outcome让球值转成浮点数用于排序和找正盘"""
    try:
        neg, val = normalize_line(raw)
        num = float(val)
        return -num if neg else num
    except:
        return 999

def fetch_pinnacle_odds(fx_id):
    """
    拉取平博(Pinnacle)开盘和当前盘口
    只取正盘（让球值绝对值最小的那条线）
    大小球用 goal_line（亚洲盘）
    返回 {"ah": {...}, "ou": {...}}
    赔率为香港赔率（欧赔-1）
    """
    result = {"ah": None, "ou": None}

    data = get(f"/odds/history/{fx_id}")
    if not data or "data" not in data:
        return result

    pinnacle = [i for i in data["data"] if i.get("bookmaker_name") == "Pinnacle"]

    # ── Asian Handicap：找正盘（abs(line)最小）──
    ah_items = [i for i in pinnacle if i.get("market_key") == "asian_handicap"]
    ah_by_line = {}
    for item in ah_items:
        outcome = item.get("outcome", "")
        parts   = outcome.split("_", 1)
        if len(parts) != 2: continue
        side, line = parts[0], parts[1]
        if line not in ah_by_line:
            ah_by_line[line] = {}
        try:
            ah_by_line[line][side] = {
                "open": round(float(item.get("opening", 0)) - 1, 2),
                "now":  round(float(item.get("closing", 0)) - 1, 2),
            }
        except: pass

    if ah_by_line:
        def balance_score(line, use_now=False):
            sides = ah_by_line[line]
            key = "now" if use_now else "open"
            h = sides.get("home", {}).get(key)
            a = sides.get("away", {}).get(key)
            if h is None or a is None: return 999
            if not (0.6 <= h <= 1.3 and 0.6 <= a <= 1.3): return 999
            return abs(h - a)

        # 开盘主盘
        best_line = min(ah_by_line.keys(), key=lambda k: balance_score(k, False))
        if balance_score(best_line, False) == 999:
            best_line = min(ah_by_line.keys(), key=lambda k: abs(
                (ah_by_line[k].get("home",{}).get("open") or 999) -
                (ah_by_line[k].get("away",{}).get("open") or 999)
            ))
        sides = ah_by_line[best_line]
        home  = sides.get("home", {})
        away  = sides.get("away", {})

        # 当前：找最接近均势的3条线（排除开盘主盘）
        valid_now = sorted(
            [k for k in ah_by_line.keys() if balance_score(k, True) < 999],
            key=lambda k: balance_score(k, True)
        )
        now_lines = []
        for k in valid_now[:3]:
            s = ah_by_line[k]
            now_lines.append({
                "line":     parse_line(k),
                "home_now": s.get("home",{}).get("now"),
                "away_now": s.get("away",{}).get("now"),
            })

        result["ah"] = {
            "line":      parse_line(best_line),
            "home_open": home.get("open"),
            "home_now":  home.get("now"),
            "away_open": away.get("open"),
            "away_now":  away.get("now"),
            "now_lines": now_lines,
        }

    # ── Goal Line（亚洲盘大小球），fallback到total_goals ──
    gl_items = [i for i in pinnacle if i.get("market_key") == "goal_line"]
    if not gl_items:
        gl_items = [i for i in pinnacle if i.get("market_key") == "total_goals"]
    gl_by_line = {}
    for item in gl_items:
        outcome = item.get("outcome", "")  # over_3, under_35 etc
        parts   = outcome.split("_", 1)
        if len(parts) != 2: continue
        side, line = parts[0], parts[1]
        # 格式化：3→3, 35→3.5
        if len(line) == 2 and line[1] != "0":
            line_fmt = line[0] + "." + line[1]
        else:
            line_fmt = line
        if line_fmt not in gl_by_line:
            gl_by_line[line_fmt] = {}
        try:
            gl_by_line[line_fmt][side] = {
                "open": round(float(item.get("opening", 0)) - 1, 2),
                "now":  round(float(item.get("closing", 0)) - 1, 2),
            }
        except: pass

    if gl_by_line:
        # 找主盘：两边赔率在合理范围且差距最小
        def ou_balance(line):
            sides = gl_by_line[line]
            o = sides.get("over",  {}).get("open")
            u = sides.get("under", {}).get("open")
            if o is None or u is None: return 999
            if not (0.6 <= o <= 1.3 and 0.6 <= u <= 1.3): return 999
            return abs(o - u)
        best_line = min(gl_by_line.keys(), key=ou_balance)
        if ou_balance(best_line) == 999:
            best_line = min(gl_by_line.keys(), key=lambda k: abs(
                (gl_by_line[k].get("over",{}).get("open") or 999) -
                (gl_by_line[k].get("under",{}).get("open") or 999)
            ))
        sides     = gl_by_line[best_line]
        over      = sides.get("over",  {})
        under     = sides.get("under", {})
        result["ou"] = {
            "line":       best_line,
            "over_open":  over.get("open"),
            "over_now":   over.get("now"),
            "under_open": under.get("open"),
            "under_now":  under.get("now"),
        }

    return result

# ─────────────────────────────────────────
# 显示模型 vs 蒙特卡洛对比
# ─────────────────────────────────────────
def show_comparison(fx):
    prob = fx.get("prob") or {}
    sim  = fx.get("sim")  or {}

    sep("=")
    print(f"  预测模型 vs 蒙特卡洛模拟（50k次）  ·  {fx['match']}")
    sep()

    def row(label, model_val, sim_val, warn=False):
        diff = abs(model_val - sim_val) if model_val is not None and sim_val is not None else None
        flag = " ⚠" if diff and diff > DIVERGENCE_THRESHOLD else ""
        diff_str = f"{diff:.1f}%" if diff is not None else "  —"
        print(f"  {label:<20} {fmtp(model_val):>10} {fmtp(sim_val):>12}  {diff_str:>8}{flag}")

    print(f"  {'指标':<20} {'预测模型':>10} {'蒙特卡洛':>12}  {'分歧':>8}")
    sep()

    # 全场1X2
    print("  [全场 1X2]")
    row("  主队胜%",  prob.get("home_win"),        sim.get("home_win_percentage"))
    row("  平局%",    prob.get("draw"),             sim.get("draw_percentage"))
    row("  客队胜%",  prob.get("away_win"),         sim.get("away_win_percentage"))

    # 半场1X2
    print("\n  [半场 1X2]")
    sim_ht = sim.get("first_half") or {}
    row("  主队胜%",  prob.get("home_win_ht"),      sim_ht.get("home_win_percentage"))
    row("  平局%",    prob.get("draw_ht"),           sim_ht.get("draw_percentage"))
    row("  客队胜%",  prob.get("away_win_ht"),       sim_ht.get("away_win_percentage"))

    # BTTS
    print("\n  [BTTS]")
    row("  双方进球%", prob.get("btts"),             sim.get("btts_percentage"))
    row("  无BTTS%",  prob.get("btts_no"),           sim.get("btts_no_percentage"))

    # 大小球
    print("\n  [大小球]")
    row("  大1.5%",   prob.get("o15"),              sim.get("o15_goals_percentage"))
    row("  大2.5%",   prob.get("o25"),              sim.get("o25_goals_percentage"))
    row("  大3.5%",   prob.get("o35"),              sim.get("o35_goals_percentage"))

    # xG（只有模拟有）
    xg = sim.get("expected_goals") or {}
    if xg:
        print("\n  [期望进球 xG（蒙特卡洛）]")
        print(f"  {'主队 xG':<20} {fmt(xg.get('home'), 2):>10}")
        print(f"  {'客队 xG':<20} {fmt(xg.get('away'), 2):>10}")
        print(f"  {'总 xG':<20} {fmt(xg.get('total'), 2):>10}")

    # 亚洲盘（模拟直接给出）
    ah = sim.get("asian_handicap") or {}
    if ah:
        print("\n  [亚洲盘概率（蒙特卡洛直接输出）]")
        for k, v in ah.items():
            print(f"  {k:<20} {fmtp(v):>10}")

    # ── 平博赔率：开盘 vs 当前 ──
    pinnacle = fx.get("pinnacle") or {}
    ah       = pinnacle.get("ah")
    ou       = pinnacle.get("ou")

    def move(now, open_):
        if now is None or open_ is None: return ""
        if now > open_: return " ↑"
        if now < open_: return " ↓"
        return ""

    if ah or ou:
        print(f"\n  [平博赔率（香港赔率）]")
        sep()
        print(f"  {'':20}  {'主队':>8}  {'盘口':^8}  {'客队':>8}")
        sep()
        if ah:
            def ah_label(raw_line):
                """
                把让球值转成清晰文字
                OA定义：正数=主队受让（客队让球），负数=主队让球
                例：+1.5 → 客让1.5  -1.5 → 主让1.5  0 → 平手盘
                返回：(主队标签, 盘口描述, 客队标签)
                """
                try:
                    v = float(raw_line)
                    # 格式化数字：去掉不必要的小数位，保留精度
                    def fv(n):
                        n = abs(n)
                        s = f"{n:.2f}".rstrip("0").rstrip(".")
                        return s
                    vs = fv(v)
                    if v > 0:
                        return f"受让{vs}球", f"客让{vs}", f"让{vs}球"
                    elif v < 0:
                        return f"让{vs}球", f"主让{vs}", f"受让{vs}球"
                    else:
                        return "平手盘", "平手", "平手盘"
                except:
                    return raw_line, raw_line, raw_line

            home_lbl, line_desc, away_lbl = ah_label(ah.get("line","?"))
            ho = f"{ah['home_open']:.2f}" if ah.get("home_open") is not None else "—"
            ao = f"{ah['away_open']:.2f}" if ah.get("away_open") is not None else "—"
            hn = f"{ah['home_now']:.2f}{move(ah.get('home_now'), ah.get('home_open'))}" if ah.get("home_now") is not None else "—"
            an = f"{ah['away_now']:.2f}{move(ah.get('away_now'), ah.get('away_open'))}" if ah.get("away_now") is not None else "—"

            print(f"  {'':14} {'主队':>8}  {'盘口':^12}  {'客队':>8}")
            print(f"  {'亚洲盘 开盘':<14} {ho:>8}  {line_desc:^12}  {ao:>8}")
            print(f"  {'亚洲盘 当前':<14} {hn:>8}  {line_desc:^12}  {an:>8}")

            # 当前附近2条线
            now_lines = ah.get("now_lines") or []
            if now_lines:
                print(f"  当前附近盘口:")
                for nl in now_lines[:2]:
                    _, nl_desc, _ = ah_label(nl.get("line","?"))
                    nhn = f"{nl['home_now']:.2f}" if nl.get("home_now") is not None else "—"
                    nan = f"{nl['away_now']:.2f}" if nl.get("away_now") is not None else "—"
                    print(f"  {'':14} {nhn:>8}  {nl_desc:^12}  {nan:>8}")
        if ou:
            line = "大/小 " + str(ou.get("line","?"))
            oo   = f"{ou['over_open']:.2f}"  if ou.get("over_open")  is not None else "—"
            uo   = f"{ou['under_open']:.2f}" if ou.get("under_open") is not None else "—"
            on_  = f"{ou['over_now']:.2f}{move(ou.get('over_now'), ou.get('over_open'))}"   if ou.get("over_now")  is not None else "—"
            un_  = f"{ou['under_now']:.2f}{move(ou.get('under_now'), ou.get('under_open'))}" if ou.get("under_now") is not None else "—"
            print(f"  {'大小球 开盘':<20}  {oo:>8}  {line:^8}  {uo:>8}")
            print(f"  {'大小球 当前':<20}  {on_:>8}  {line:^8}  {un_:>8}")
        sep()
    else:
        print(f"\n  [平博赔率] 无数据（该场次尚未开盘）")

    sep()

    # 计算总体分歧度
    diffs = []
    for m_val, s_val in [
        (prob.get("home_win"), sim.get("home_win_percentage")),
        (prob.get("draw"),     sim.get("draw_percentage")),
        (prob.get("away_win"), sim.get("away_win_percentage")),
        (prob.get("o25"),      sim.get("o25_goals_percentage")),
    ]:
        if m_val is not None and s_val is not None:
            diffs.append(abs(m_val - s_val))

    max_div = max(diffs) if diffs else 0
    if max_div > DIVERGENCE_THRESHOLD:
        print(f"  ⚠  高分歧警告：最大分歧 {max_div:.1f}% > {DIVERGENCE_THRESHOLD}%")
        print(f"     两个模型对这场比赛判断差异较大，建议谨慎")
    else:
        print(f"  ✓  模型一致性良好（最大分歧 {max_div:.1f}%）")
    sep("=")
    return max_div > DIVERGENCE_THRESHOLD

# ─────────────────────────────────────────
# 显示正确比分
# ─────────────────────────────────────────
def show_scores(fx):
    prob   = fx.get("prob") or {}
    sim    = fx.get("sim")  or {}

    model_scores = prob.get("correct_scores") or {}
    sim_scores   = sim.get("scorelines")      or {}

    sep("=")
    print(f"  正确比分对比  ·  {fx['match']}")
    sep()

    other_labels = {
        "other_1": "主队大胜(3-0/4-0等)",
        "other_2": "客队大胜(0-3/0-4等)",
        "other_x": "高分平局(2-2/3-3等)",
    }

    # 合并所有比分
    all_scores = set(list(model_scores.keys()) + list(sim_scores.keys()))

    # 分离Other
    others    = {k: k for k in all_scores if "other" in k.lower()}
    specifics = {k for k in all_scores if "other" not in k.lower()}

    # 排序（按模拟概率）
    sorted_specific = sorted(specifics, key=lambda k: -(sim_scores.get(k) or 0))

    print(f"  {'比分':<12} {'预测模型':>10} {'蒙特卡洛':>10}")
    sep()

    # Other先显示
    for k in ["other_1", "other_2", "other_x"]:
        mv = model_scores.get(k)
        sv = sim_scores.get(k)
        label = other_labels.get(k, k)
        if mv is not None or sv is not None:
            bar = "#" * min(round((sv or 0) / 1.5), 20)
            print(f"  {k:<12} {fmtp(mv):>10} {fmtp(sv):>10}  {bar}  <- {label}")

    sep()
    print("  [具体比分（概率 >= 5%）]")
    sep()
    shown = 0
    for k in sorted_specific:
        mv = model_scores.get(k)
        sv = sim_scores.get(k)
        if (sv or 0) < 5 and (mv or 0) < 5:
            continue
        bar = "#" * min(round((sv or 0) / 1.5), 20)
        print(f"  {k:<12} {fmtp(mv):>10} {fmtp(sv):>10}  {bar}")
        shown += 1
    if shown == 0:
        print("  — 无概率 >= 5% 的具体比分")

# ─────────────────────────────────────────
# 显示H2H
# ─────────────────────────────────────────
def show_h2h(fx):
    h2h = fx.get("h2h") or []
    home, away = fx["home"], fx["away"]

    sep("=")
    print(f"  H2H历史  ·  {home} vs {away}")
    sep()

    if not h2h:
        print("  — 无H2H数据")
        sep("=")
        return

    # 统计（以当前主队为team1视角）
    t1w = t2w = draws = 0
    o25 = btts_cnt = 0
    for h in h2h:
        if h.get("team1_win"):   t1w += 1
        elif h.get("team2_win"): t2w += 1
        else:                    draws += 1
        if h.get("over_25"):     o25 += 1
        if h.get("btts"):        btts_cnt += 1

    total = len(h2h)
    print(f"  近{total}场：{home} 胜 {t1w}  平 {draws}  {away} 胜 {t2w}")
    print(f"  大球2.5+：{o25}/{total} ({o25/total*100:.0f}%)  BTTS：{btts_cnt}/{total} ({btts_cnt/total*100:.0f}%)")

    # 克制关系判断
    print(f"\n  克制分析：")
    if t1w > t2w * 1.5:
        print(f"  → {home} 历史上压制 {away}（胜率{t1w/total*100:.0f}%）")
    elif t2w > t1w * 1.5:
        print(f"  → {away} 历史上压制 {home}（胜率{t2w/total*100:.0f}%）")
    else:
        print(f"  → 双方历史势均力敌，无明显克制关系")

    if o25/total >= 0.6:
        print(f"  → 历史大球场次多（{o25/total*100:.0f}%），偏向大球")
    elif o25/total <= 0.4:
        print(f"  → 历史小球场次多（{o25/total*100:.0f}%），偏向小球")

    print(f"\n  最近{min(6,total)}场对阵：")
    sep()
    for h in h2h[:6]:
        score  = f"{h.get('home_goals',0)}-{h.get('away_goals',0)}"
        result = "主胜" if h.get("home_win") else ("客胜" if h.get("away_win") else "平局")
        ou     = "大" if h.get("over_25") else "小"
        btts_s = "Y" if h.get("btts") else "N"
        print(f"  {h.get('date',''):<15} {h.get('home_name',''):<22} {score:>5}  {h.get('away_name',''):<22}  {result}  O/U:{ou}  BTTS:{btts_s}")
    sep("=")

# ─────────────────────────────────────────
# 显示球队近期数据（Scored/Conceded/xG）
# ─────────────────────────────────────────
def show_team_stats(fx):
    stats  = fx.get("team_stats") or {}
    sim    = fx.get("sim")        or {}
    xg_sim = sim.get("expected_goals") or {}

    h5 = stats.get("home_5h") or {}
    a5 = stats.get("away_5a") or {}
    h10= stats.get("home_10") or {}
    a10= stats.get("away_10") or {}

    hn = fx["home"]
    an = fx["away"]

    sep("=")
    print(f"  球队近期数据  ·  {fx['match']}")

    def gv(s, key, sub=None):
        """安全取值"""
        if not s: return None
        val = s.get(key) or {}
        if sub: return val.get(sub)
        return val

    def fn(v):
        """数字格式化"""
        if v is None: return "  —  "
        return f"{v:.2f}"

    def fp(v):
        """百分比格式化"""
        if v is None: return "  —  "
        return f"{int(v)}%"

    def ppg(s):
        if not s: return None
        return (s.get("points") or {}).get("total_avg")

    def ppg_home(s):
        if not s: return None
        return (s.get("points") or {}).get("home_avg")

    def ppg_away(s):
        if not s: return None
        return (s.get("points") or {}).get("away_avg")

    def row(label, hv, av, is_pct=False):
        """打印对齐行"""
        fmt = fp if is_pct else fn
        hs  = fmt(hv) if not isinstance(hv, str) else (hv if hv else "  —  ")
        as_ = fmt(av) if not isinstance(av, str) else (av if av else "  —  ")
        print(f"  {label:<18} {hs:>10}          {as_:>10}")

    W = 22  # 列宽

    # ══ 近5场主场 vs 客场 ══
    h5p = (h5.get("played") or {}).get("total", 0)
    a5p = (a5.get("played") or {}).get("total", 0)
    sep()
    print(f"  {'':18} {'主队 近'+str(h5p)+'场主场':>10}          {'客队 近'+str(a5p)+'场客场':>10}")
    print(f"  {'':18} {hn[:10]:>10}          {an[:10]:>10}")
    sep()

    h5_o25  = ((h5.get("goals_over")  or {}).get("o2") or {}).get("total_percentage")
    a5_o25  = ((a5.get("goals_over")  or {}).get("o2") or {}).get("total_percentage")
    h10_o25 = ((h10.get("goals_over") or {}).get("o2") or {}).get("total_percentage")
    a10_o25 = ((a10.get("goals_over") or {}).get("o2") or {}).get("total_percentage")

    # PPG一行：主队主场PPG / 客队客场PPG
    h_ppg = ppg_home(h5)
    a_ppg = ppg_away(a5)
    row("PPG（主/客场）",   h_ppg,  a_ppg)
    row("Scored 场均",      gv(h5,"goals_for","total_avg"),         gv(a5,"goals_for","total_avg"))
    row("Conceded 场均",    gv(h5,"goals_against","total_avg"),     gv(a5,"goals_against","total_avg"))
    row("xG (模拟)",        xg_sim.get("home"),                     xg_sim.get("away"))
    row("Clean Sheet",      gv(h5,"clean_sheet","total_percentage"),    gv(a5,"clean_sheet","total_percentage"),    True)
    row("Failed to Score",  gv(h5,"failed_to_score","total_percentage"),gv(a5,"failed_to_score","total_percentage"),True)
    row("BTTS",             gv(h5,"btts","total_percentage"),       gv(a5,"btts","total_percentage"),       True)
    row("大2.5",            h5_o25,                                 a5_o25,                                 True)

    # ══ 近10场总体 ══
    h10p = (h10.get("played") or {}).get("total", 0)
    a10p = (a10.get("played") or {}).get("total", 0)
    sep()
    print(f"  {'':18} {'主队 近'+str(h10p)+'场总体':>10}          {'客队 近'+str(a10p)+'场总体':>10}")
    print(f"  {'':18} {hn[:10]:>10}          {an[:10]:>10}")
    sep()

    row("PPG",              ppg(h10),                               ppg(a10))
    row("Scored 场均",      gv(h10,"goals_for","total_avg"),        gv(a10,"goals_for","total_avg"))
    row("Conceded 场均",    gv(h10,"goals_against","total_avg"),    gv(a10,"goals_against","total_avg"))
    row("Clean Sheet",      gv(h10,"clean_sheet","total_percentage"),   gv(a10,"clean_sheet","total_percentage"),   True)
    row("Failed to Score",  gv(h10,"failed_to_score","total_percentage"),gv(a10,"failed_to_score","total_percentage"),True)
    row("BTTS",             gv(h10,"btts","total_percentage"),      gv(a10,"btts","total_percentage"),      True)
    row("大2.5",            h10_o25,                                a10_o25,                                True)

    sep("=")

# ─────────────────────────────────────────
# 泊松 + 亚洲让球
# ─────────────────────────────────────────
def poisson(k, lam):
    if k < 0 or lam <= 0: return 0
    lp = -lam + k * math.log(lam)
    for i in range(1, k+1): lp -= math.log(i)
    return math.exp(lp)

def build_matrix(l1, l2, N=9):
    return [[poisson(i,l1)*poisson(j,l2) for j in range(N+1)] for i in range(N+1)]

def matrix_1x2(m):
    w=d=l=0
    for i,row in enumerate(m):
        for j,cell in enumerate(row):
            if i>j: w+=cell
            elif i==j: d+=cell
            else: l+=cell
    return w,d,l

def solve_lambda(ph, pd, pa):
    best, bE = (1.4,1.1), 1e9
    step = [x*0.06+0.2 for x in range(72)]
    for l1 in step:
        for l2 in step:
            w,d,l = matrix_1x2(build_matrix(l1,l2))
            e = (w-ph)**2+(d-pd)**2+(l-pa)**2
            if e<bE: bE=e; best=(l1,l2)
    l1,l2 = best
    for _ in range(800):
        imp = False
        for s in [0.005,0.001,0.0002]:
            for d1,d2 in [(s,0),(-s,0),(0,s),(0,-s),(s,s),(-s,-s),(s,-s),(-s,s)]:
                nl1,nl2 = l1+d1,l2+d2
                if nl1<0.05 or nl2<0.05: continue
                w,d,l = matrix_1x2(build_matrix(nl1,nl2))
                e=(w-ph)**2+(d-pd)**2+(l-pa)**2
                if e<bE: bE=e; l1,l2=nl1,nl2; imp=True
        if not imp: break
    return l1,l2

def pure_ah(m, line):
    h=p=a=0
    for i,row in enumerate(m):
        for j,cell in enumerate(row):
            diff=(i-j)+line
            if abs(diff)<0.001: p+=cell
            elif diff>0: h+=cell
            else: a+=cell
    return h,p,a

def get_ah(m, line):
    if round(line*4)%2!=0:
        lo=math.floor(line*2)/2
        h1,p1,a1=pure_ah(m,lo)
        h2,p2,a2=pure_ah(m,lo+0.5)
        return (h1+h2)/2,(p1+p2)/2,(a1+a2)/2
    return pure_ah(m,line)

AH_LINES = [
    ("客让 -2.0  / 主受 +2.0",   2.0),
    ("客让 -1.75 / 主受 +1.75",  1.75),
    ("客让 -1.5  / 主受 +1.5",   1.5),
    ("客让 -1.25 / 主受 +1.25",  1.25),
    ("客让 -1.0  / 主受 +1.0",   1.0),
    ("客让 -0.75 / 主受 +0.75",  0.75),
    ("客让 -0.5  / 主受 +0.5",   0.5),
    ("客让 -0.25 / 主受 +0.25",  0.25),
    ("平手盘 (0)",                0),
    ("主让 -0.25 / 客受 +0.25", -0.25),
    ("主让 -0.5  / 客受 +0.5",  -0.5),
    ("主让 -0.75 / 客受 +0.75", -0.75),
    ("主让 -1.0  / 客受 +1.0",  -1.0),
    ("主让 -1.25 / 客受 +1.25", -1.25),
    ("主让 -1.5  / 客受 +1.5",  -1.5),
    ("主让 -1.75 / 客受 +1.75", -1.75),
    ("主让 -2.0  / 客受 +2.0",  -2.0),
]

def show_ah_table(fx, high_div, use_sim=True):
    # 优先用蒙特卡洛的1X2（更可靠），备用预测模型
    sim  = fx.get("sim")  or {}
    prob = fx.get("prob") or {}

    if use_sim and sim.get("home_win_percentage"):
        ph = sim["home_win_percentage"]
        pd_= sim["draw_percentage"]
        pa = sim["away_win_percentage"]
        src = "蒙特卡洛"
    else:
        ph = prob.get("home_win")
        pd_= prob.get("draw")
        pa = prob.get("away_win")
        src = "预测模型"

    if not all([ph, pd_, pa]):
        print("  缺少1X2概率，无法计算")
        return None

    # 归一化
    total = ph + pd_ + pa
    ph, pd_, pa = ph/total*100, pd_/total*100, pa/total*100

    l1, l2 = solve_lambda(ph/100, pd_/100, pa/100)
    matrix = build_matrix(l1, l2)

    sep("=")
    print(f"  亚洲让球概率表  ·  {fx['match']}")
    print(f"  数据来源: {src}  |  λ主={l1:.3f} λ客={l2:.3f}")
    print(f"  1X2: 主{ph:.1f}% 平{pd_:.1f}% 客{pa:.1f}%")
    if high_div:
        print(f"  ⚠ 两模型分歧较大，结果仅供参考")

    # 同时显示蒙特卡洛直接给出的AH概率
    ah_sim = sim.get("asian_handicap") or {}
    if ah_sim:
        print(f"\n  [蒙特卡洛亚洲盘概率（前4）]")
        # 只取概率最高的4个
        sorted_ah = sorted(ah_sim.items(), key=lambda x: -(x[1] or 0))[:4]
        for k, v in sorted_ah:
            print(f"    {k:<20} {fmtp(v)}")

    sep()
    print(f"  {'盘口':<32} {'主赢%':>7} {'走水%':>7} {'客赢%':>7}   {'主有效%':>8} {'客有效%':>8}")
    sep()
    for label, line in AH_LINES:
        rH,rP,rA = get_ah(matrix, line)
        effH = rH/(rH+rA) if (rH+rA)>0 else 0
        effA = rA/(rH+rA) if (rH+rA)>0 else 0
        push_str = f"{rP*100:6.1f}%" if rP>0.004 else "    -- "
        print(f"  {label:<32} {rH*100:7.1f}%{push_str:>8} {rA*100:7.1f}%   {effH*100:7.1f}% {effA*100:7.1f}%")
    sep("=")
    return matrix

def calc_ev(fx, matrix, high_div):
    ev_threshold = 0.08 if high_div else 0.05
    t_label = "8%（高分歧）" if high_div else "5%"

    print(f"\n  选择盘口（输入编号）  EV门槛: {t_label}")
    for i,(label,line) in enumerate(AH_LINES):
        print(f"  {i+1:>2}. {label}")
    print("   0. 返回")

    choice = input("\n  请输入编号: ").strip()
    if choice == "0": return
    try:
        idx = int(choice)-1
        if not (0<=idx<len(AH_LINES)):
            print("  无效编号"); return
    except:
        print("  请输入数字"); return

    label, line = AH_LINES[idx]
    rH,rP,rA = get_ah(matrix, line)
    effH = rH/(rH+rA) if (rH+rA)>0 else 0
    effA = rA/(rH+rA) if (rH+rA)>0 else 0

    print(f"\n  盘口: {label}")
    print(f"  主有效%: {effH*100:.2f}%  客有效%: {effA*100:.2f}%  走水: {rP*100:.2f}%")

    try:
        oH = float(input("\n  主队香港赔率: ").strip())
        oA = float(input("  客队香港赔率: ").strip())
    except:
        print("  请输入有效数字"); return

    evH = effH*oH - effA
    evA = effA*oA - effH
    tH  = (ev_threshold+effA)/effH if effH>0 else 0
    tA  = (ev_threshold+effH)/effA if effA>0 else 0

    def tag(ev):
        if ev>=ev_threshold: return f">> 有优势 EV>{t_label}"
        if ev>=0: return ">> 微弱正EV，观望"
        return ">> 负EV，跳过"

    sep()
    print(f"\n  [EV结果]  {label}")
    sep()
    print(f"  投主队: {effH*100:.2f}% x {oH} - {effA*100:.2f}% = {evH*100:+.2f}%  {tag(evH)}")
    if evH < ev_threshold:
        print(f"           需赔率 >= {tH:.3f} 才达门槛")
    print(f"  投客队: {effA*100:.2f}% x {oA} - {effH*100:.2f}% = {evA*100:+.2f}%  {tag(evA)}")
    if evA < ev_threshold:
        print(f"           需赔率 >= {tA:.3f} 才达门槛")
    sep()

# ─────────────────────────────────────────
# 拉取球队近期stats
# ─────────────────────────────────────────
def fetch_team_stats(season_id, home_id, away_id):
    """
    拉取三组数据：
    - home_5h: 主队近5场主场数据
    - away_5a: 客队近5场客场数据
    - home_10: 主队近10场总体数据
    - away_10: 客队近10场总体数据
    """
    def extract(data, team_id):
        if not data or "data" not in data: return None
        for team in data["data"]:
            if team.get("team_id") == team_id:
                return team
        return None

    # 近5场主场（主队用）
    d_home = get(f"/stats/season/{season_id}", {"last_x": "5_home",    "include_frozen": "false"})
    # 近5场客场（客队用）
    d_away = get(f"/stats/season/{season_id}", {"last_x": "5_away",    "include_frozen": "false"})
    # 近10场总体（主客队都用）
    d_10   = get(f"/stats/season/{season_id}", {"last_x": "10_overall","include_frozen": "false"})

    return {
        "home_5h": extract(d_home, home_id),   # 主队近5主场
        "away_5a": extract(d_away, away_id),   # 客队近5客场
        "home_10": extract(d_10,   home_id),   # 主队近10总体
        "away_10": extract(d_10,   away_id),   # 客队近10总体
    }

# ─────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────
def main():
    print("\n" + "="*72)
    print("  OddAlerts 分析工具  —  预测模型 vs 蒙特卡洛 + H2H + 球队数据")
    print("="*72)

    if "YOUR_" in API_TOKEN:
        print("\n  请先填入你的OddAlerts API Token！")
        return

    # 选日期
    tomorrow = str(date.today() + timedelta(days=1))
    print(f"\n  默认日期: 明天 ({tomorrow})")
    d = input("  输入日期 (YYYY-MM-DD，回车用明天): ").strip()
    target_date = d if d else tomorrow

    # 拉取热门比赛（popular端点）
    print(f"\n  正在拉取 {target_date} 的热门比赛...")
    data = get("/fixtures/popular", {"per_page": "500", "include": "probability"})
    if not data or not data.get("data"):
        print("  无法获取比赛列表，请检查网络和Token")
        return

    all_fx = [fx for fx in data["data"] if fx.get("date","")[:10] == target_date]

    if not all_fx:
        print(f"  {target_date} 暂无热门比赛")
        retry = input("\n  重新输入日期（回车退出）: ").strip()
        if not retry:
            return
        target_date = retry
        all_fx = [fx for fx in data["data"] if fx.get("date","")[:10] == target_date]
        if not all_fx:
            print(f"  {target_date} 仍无比赛")
            return

    # 联赛筛选
    leagues = {}
    for fx in all_fx:
        lid = fx.get("competition_id")
        if lid not in leagues:
            leagues[lid] = {
                "name":          fx.get("competition_name", ""),
                "country":       fx.get("competition_country", ""),
                "type":          fx.get("competition_type", ""),
                "predictability": fx.get("competition_predictability"),
            }

    # ── 大循环：支持返回联赛选择 ──
    while True:
        # 按国家名排序
        league_list = sorted(
            leagues.items(),
            key=lambda x: (x[1]["country"].lower(), x[1]["name"].lower())
        )

        print(f"\n  找到 {len(all_fx)} 场比赛，涉及 {len(leagues)} 个联赛")
        print(f"\n  {'#':>3}  {'国家':<20}  {'联赛名称':<32}  {'可预测性'}")
        print(f"  {'-'*3}  {'-'*20}  {'-'*32}  {'-'*12}")
        pred_map = {
            "great":   "★★★★ great",
            "high":    "★★★★ great",
            "good":    "★★★  good",
            "medium":  "★★★  good",
            "average": "★★   avg",
            "low":     "★    poor",
            "poor":    "★    poor",
            None:      "--",
        }
        for i, (lid, info) in enumerate(league_list):
            country = info["country"] or "Unknown"
            name    = info["name"]
            pred    = pred_map.get(info.get("predictability"), info.get("predictability") or "--")
            print(f"  {i+1:>3}  {country:<20}  {name:<32}  {pred}")
        print(f"\n  可预测性: ★★★★great=容易  ★★★good=较好  ★★avg=一般  ★poor=难  --=无数据")
        print("  输入联赛编号过滤（逗号分隔，回车显示全部）| 0 退出程序")
        filter_input = input("  请输入: ").strip()

        if filter_input == "0":
            print("\n  再见！")
            break

        if filter_input:
            selected_ids = set()
            for c in filter_input.split(","):
                c = c.strip()
                if c.isdigit():
                    idx = int(c)-1
                    if 0 <= idx < len(league_list):
                        selected_ids.add(league_list[idx][0])
            filtered_fx = [fx for fx in all_fx if fx.get("competition_id") in selected_ids]
            print(f"  过滤后: {len(filtered_fx)} 场")
        else:
            filtered_fx = all_fx

        # 构建比赛列表（保留已加载数据）
        existing = {fx["oa_id"]: fx for fx in fixtures} if "fixtures" in dir() else {}
        fixtures = []
        for fx in filtered_fx:
            if fx["id"] in existing:
                fixtures.append(existing[fx["id"]])
            else:
                fixtures.append({
                    "oa_id":          fx["id"],
                    "match":          f"{fx['home_name']} vs {fx['away_name']}",
                    "home":           fx["home_name"],
                    "away":           fx["away_name"],
                    "kickoff":        fx.get("date",""),
                    "league":         fx.get("competition_name",""),
                    "country":        fx.get("competition_country",""),
                    "predictability": fx.get("competition_predictability"),
                    "season_id":      fx.get("season_id"),
                    "home_id":        fx.get("home_id"),
                    "away_id":        fx.get("away_id"),
                    "prob":           fx.get("probability") or {},
                    "sim":            {},
                    "h2h":            [],
                    "team_stats":     {},
                    "loaded":         False,
                    "pinnacle":       {"ah": None, "ou": None},
                })

        # 比赛列表循环
        while True:
            return_to_league = False
            show_list(fixtures)
            print("  输入比赛编号 | 0 返回联赛选择 | 9 退出程序")
            choice = input("  请输入: ").strip()

            if choice == "9":
                print("\n  再见！")
                return
            if choice == "0":
                break
            try:
                idx = int(choice)-1
                if not (0<=idx<len(fixtures)):
                    print("  无效编号"); continue
            except:
                print("  请输入数字"); continue

            fx = fixtures[idx]

            # 按需拉取详细数据
            if not fx["loaded"]:
                print(f"\n  正在拉取 {fx['match']} 的数据...")

                # 蒙特卡洛模拟
                sim_data = get(f"/predictions/generate/{fx['oa_id']}")
                if sim_data and "data" in sim_data and sim_data["data"]:
                    fx["sim"] = sim_data["data"][0]
                    print(f"  ✓ 蒙特卡洛模拟")

                # H2H + correct_scores
                detail = get(f"/fixtures/{fx['oa_id']}", {
                    "include": "h2h,correctScores"
                })
                if detail and "data" in detail and detail["data"]:
                    d = detail["data"][0]
                    fx["h2h"]  = d.get("h2h", [])[:6]  # 只取最近6场
                    # 把correct_scores合并到prob
                    if d.get("correct_scores"):
                        fx["prob"]["correct_scores"] = d["correct_scores"]
                    print(f"  ✓ H2H（{len(fx['h2h'])}场）+ 正确比分")

                # 球队近期stats（三组：5场同主客 + 10场总体）
                if fx["season_id"] and fx["home_id"] and fx["away_id"]:
                    fx["team_stats"] = fetch_team_stats(fx["season_id"], fx["home_id"], fx["away_id"])
                    print(f"  ✓ 球队近期数据")

                # 平博开盘赔率
            print(f"  正在拉取平博开盘赔率...")
            fx["pinnacle"] = fetch_pinnacle_odds(fx["oa_id"])
            if fx["pinnacle"].get("ah") or fx["pinnacle"].get("ou"):
                print(f"  ✓ 平博开盘赔率")
            else:
                print(f"  ⚠ 无平博赔率数据")

            fx["loaded"] = True

            # 单场：直接显示所有数据
            high_div = False
            matrix   = None
            return_to_league = False

            # 自动显示 1~4 所有数据
            high_div = show_comparison(fx)
            show_scores(fx)
            show_h2h(fx)
            show_team_stats(fx)

            # 操作菜单
            while True:
                sep("=")
                pred = fx.get("predictability") or "--"
                print(f"  {fx['match']}  |  {fx['kickoff'][:16]}  |  {fx['league']}  |  可预测性: {pred}")
                sep()
                print("  5. 亚洲让球概率表")
                print("  6. 计算EV")
                print("  8. 返回比赛列表（同一联赛）")
                print("  0. 返回联赛选择")
                sub = input("\n  请选择: ").strip()

                if sub == "0":
                    return_to_league = True
                    break
                elif sub == "8":
                    break
                elif sub == "5":
                    matrix = show_ah_table(fx, high_div)
                    input("\n  按回车继续...")
                elif sub == "6":
                    if matrix is None:
                        matrix = show_ah_table(fx, high_div)
                    calc_ev(fx, matrix, high_div)
                    input("\n  按回车继续...")
                else:
                    print("  无效选项")

                if return_to_league:
                    break
            # 把 return_to_league 传递给外层比赛列表循环
            if return_to_league:
                break  # 跳出比赛列表循环，回到联赛选择

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  错误: {e}")
        import traceback
        traceback.print_exc()
    print("\n  结果已保存到 oa_output.txt")
    input("按回车键退出...")
