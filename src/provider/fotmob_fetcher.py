"""
FotMob 数据获取工具
支持：今日比赛、联赛详情、比赛详情、球队信息
"""

import requests
import json
import time
import random
from datetime import datetime


# ── 配置 ──────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.fotmob.com/",
    "Origin": "https://www.fotmob.com",
}

BASE_URL = "https://www.fotmob.com/api"

# 常用联赛 ID
LEAGUES = {
    "英超": 47,
    "西甲": 87,
    "意甲": 55,
    "德甲": 54,
    "法甲": 53,
    "欧冠": 42,
    "中超": 1349,
}


# ── 核心请求函数 ──────────────────────────────────────
class FotMobClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._warm_up()

    def _warm_up(self):
        """先访问主页，获取 Cookie，模拟真实浏览器行为"""
        try:
            self.session.get("https://www.fotmob.com/", timeout=10)
            time.sleep(random.uniform(0.5, 1.2))
        except Exception:
            pass  # 预热失败不影响后续请求

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """通用 GET 请求，带重试"""
        url = f"{BASE_URL}/{endpoint}"
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                resp.raise_for_status()
                time.sleep(random.uniform(0.8, 2.0))  # 礼貌性延迟
                return resp.json()
            except requests.exceptions.HTTPError as e:
                print(f"  ✗ HTTP 错误 {e.response.status_code}，第 {attempt+1} 次重试...")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  ✗ 请求失败: {e}，第 {attempt+1} 次重试...")
                time.sleep(2 ** attempt)
        raise RuntimeError(f"请求 {url} 失败，已重试 3 次")

    # ── 接口方法 ──────────────────────────────────────

    def get_matches_by_date(self, date: str = None) -> dict:
        """
        获取指定日期的所有比赛
        :param date: 格式 'YYYYMMDD'，默认今天
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        print(f"📅 获取 {date} 的比赛...")
        return self._get("matches", {"date": date})

    def get_league(self, league_id: int, tab: str = "matches") -> dict:
        """
        获取联赛信息
        :param league_id: 联赛 ID（见 LEAGUES 字典）
        :param tab: 'matches' | 'table' | 'stats' | 'overview'
        """
        print(f"🏆 获取联赛 {league_id} 数据 (tab={tab})...")
        return self._get("leagues", {
            "id": league_id,
            "tab": tab,
            "type": "league",
            "timeZone": "Asia/Shanghai",
        })

    def get_match_details(self, match_id: int) -> dict:
        """获取单场比赛详情（阵容、事件、统计）"""
        print(f"⚽ 获取比赛 {match_id} 详情...")
        return self._get("matchDetails", {"matchId": match_id})

    def get_team(self, team_id: int, tab: str = "overview") -> dict:
        """
        获取球队信息
        :param tab: 'overview' | 'matches' | 'squad' | 'stats'
        """
        print(f"🏟️  获取球队 {team_id} 数据 (tab={tab})...")
        return self._get("teams", {"id": team_id, "tab": tab})

    def get_player(self, player_id: int) -> dict:
        """获取球员信息"""
        print(f"👤 获取球员 {player_id} 数据...")
        return self._get("playerData", {"id": player_id})


# ── 数据解析辅助函数 ──────────────────────────────────
def parse_matches(data: dict) -> list:
    """从 get_matches_by_date 的返回值中提取比赛列表"""
    matches = []
    for league in data.get("leagues", []):
        league_name = league.get("name", "未知联赛")
        for m in league.get("matches", []):
            status = m.get("status", {})
            matches.append({
                "联赛": league_name,
                "主队": m.get("home", {}).get("name", "-"),
                "客队": m.get("away", {}).get("name", "-"),
                "比分": status.get("scoreStr", "vs"),
                "状态": status.get("reason", {}).get("long", status.get("utcTime", "")),
                "match_id": m.get("id"),
            })
    return matches


def parse_standings(data: dict) -> list:
    """从 get_league 的返回值中提取积分榜"""
    try:
        entries = (
            data["table"]["data"][0]["table"]["all"]
        )
    except (KeyError, IndexError, TypeError):
        return []
    return [
        {
            "排名": e.get("idx"),
            "球队": e.get("name"),
            "场次": e.get("played"),
            "胜": e.get("wins"),
            "平": e.get("draws"),
            "负": e.get("losses"),
            "积分": e.get("pts"),
        }
        for e in entries
    ]


# ── 主程序示例 ────────────────────────────────────────
def main():
    client = FotMobClient()

    # ① 今日比赛
    print("\n" + "="*50)
    print("示例 1：今日比赛")
    print("="*50)
    today_data = client.get_matches_by_date()
    matches = parse_matches(today_data)
    for m in matches[:10]:
        print(f"  [{m['联赛']}] {m['主队']} {m['比分']} {m['客队']}")
    print(f"  ... 共 {len(matches)} 场比赛")

    with open("today_matches.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)
    print("  ✓ 完整数据已保存到 today_matches.json")

    # ② 英超积分榜
    print("\n" + "="*50)
    print("示例 2：英超积分榜（前 5）")
    print("="*50)
    league_data = client.get_league(LEAGUES["英超"], tab="table")
    standings = parse_standings(league_data)
    if standings:
        print(f"  {'排名':<4} {'球队':<20} {'场':<4} {'胜':<4} {'平':<4} {'负':<4} {'积分'}")
        print("  " + "-"*45)
        for row in standings[:5]:
            print(f"  {row['排名']:<4} {row['球队']:<20} {row['场次']:<4} {row['胜']:<4} {row['平']:<4} {row['负']:<4} {row['积分']}")
    else:
        print("  (积分榜暂无数据，可打印 league_data 检查结构)")

    # ③ 第一场比赛的详情
    if matches and matches[0]["match_id"]:
        print("\n" + "="*50)
        first_id = matches[0]["match_id"]
        print(f"示例 3：比赛详情 (ID={first_id})")
        print("="*50)
        detail = client.get_match_details(first_id)
        general = detail.get("general", {})
        print(f"  {general.get('homeTeam', {}).get('name')} vs {general.get('awayTeam', {}).get('name')}")
        print(f"  状态码: {general.get('matchStatusCode')}")
        with open("match_detail.json", "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)
        print("  ✓ 比赛详情已保存到 match_detail.json")


if __name__ == "__main__":
    main()
