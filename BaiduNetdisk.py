import os
import time
import json
import random
import requests
import sys  # <--- 1. 引入 sys 模块
from urllib.parse import urlparse, parse_qs

# ================= 配置区域 =================
# 从环境变量获取 Cookie
COOKIE = os.environ.get("BAIDU_COOKIE")

# 【关键点 1】: 如果没有设置 Secret，直接报错并终止，让 Action 变红
if not COOKIE:
    print("❌ 严重错误：未找到 BAIDU_COOKIE 环境变量！")
    print("请在 GitHub 仓库的 Settings -> Secrets and variables -> Actions 中添加 BAIDU_COOKIE。")
    sys.exit(1)  # <--- 终止程序，返回错误码 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://pan.baidu.com/",
    "Origin": "https://pan.baidu.com",
    "Cookie": COOKIE,
    "Content-Type": "application/json"
}

CHANNELS = [10066, 10065]
TARGET_MODULES = ["game_return_play", "new_game_play"]

def get_task_list():
    """获取任务列表"""
    all_tasks = []
    print("🔄 正在获取任务列表...")
    
    for channel in CHANNELS:
        url = f"https://wan.baidu.com/gameapi?action=bonus_pan_task_list&channel={channel}"
        try:
            res = requests.get(url, headers=HEADERS).json()
            
            # 检查是否因为 Cookie 失效导致获取列表失败
            if res.get("errorNo") == 110008:
                print(f"❌ 获取列表失败：Cookie 已失效，请更新 Secret。")
                sys.exit(1) # <--- 【关键点 2】Cookie 失效，触发 Action 失败通知

            if res.get("errorNo") == 0 and res.get("result"):
                data_list = res["result"].get("data", [])
                if isinstance(data_list, list):
                    all_tasks.extend(data_list)
        except Exception as e:
            print(f"⚠️ 获取频道 {channel} 失败: {e}")
            # 这里可以选择是否终止，如果只是网络波动可以不终止
            # sys.exit(1) 

    unique_tasks = []
    seen_ids = set()
    
    for t in all_tasks:
        if t.get("taskModule") not in TARGET_MODULES: continue
        task_id = t.get("taskId")
        if task_id in seen_ids: continue
        seen_ids.add(task_id)
        
        task_games = t.get("taskGames", [])
        if not task_games: continue
        
        game = random.choice(task_games)
        parsed_url = urlparse(game.get("gameUrl", ""))
        params = parse_qs(parsed_url.query)
        
        game_id = params.get('gameId', [None])[0]
        activity_id = params.get('activityId', [None])[0] or t.get("activityId")
        
        if not game_id: continue

        unique_tasks.append({
            "name": t.get("taskName", "未知任务"),
            "taskId": task_id,
            "gameId": game_id,
            "activityId": activity_id,
            "totalTime": t.get("eachTaskNeedPlayTimeSecs", 60)
        })
        
    print(f"✅ 获取成功，共找到 {len(unique_tasks)} 个有效任务。")
    return unique_tasks

def run_task(task):
    """执行单个任务"""
    print(f"\n🚀 开始执行任务: {task['name']}")
    remaining_time = task['totalTime']
    is_first = True
    
    while remaining_time > 0:
        params = {
            "action": "bonus_task_game_play_report",
            "gameId": task['gameId'],
            "taskId": task['taskId'],
            "activityId": task['activityId'],
            "isFirstReport": 1 if is_first else 0
        }
        
        try:
            res = requests.get("https://wan.baidu.com/gameapi", params=params, headers=HEADERS).json()
            error_no = res.get("errorNo")
            
            if error_no == 0 or error_no == 110503:
                data = res.get("result", {}).get("data", {})
                if error_no == 110503 or data.get("remainingTaskTime", 1) == 0:
                    print(f"🎉 任务 [{task['name']}] 已完成！")
                    return
                remaining_time = data.get("remainingTaskTime", remaining_time)
                print(f"⏳ [{task['name']}] 进行中... 剩余时间: {remaining_time}秒")
                
            elif error_no == 110008:
                # 【关键点 3】运行中发现 Cookie 失效
                print(f"❌ 严重错误：Cookie 已失效/未登录！")
                print("请重新抓取 Cookie 并更新到 GitHub Secrets。")
                sys.exit(1) # <--- 强制退出并报错，GitHub 会发邮件通知你
                
            else:
                print(f"⚠️ 异常状态码: {error_no}, 信息: {res}")
                if not is_first: return 

            is_first = False
            time.sleep(11) 
            
        except Exception as e:
            print(f"❌ 网络请求错误: {e}")
            # 网络错误通常是暂时的，是否要标记为失败看你选择
            # 如果希望网络不好时也报警，取消下面这行的注释：
            # sys.exit(1) 
            return

def main():
    try:
        tasks = get_task_list()
        
        if not tasks:
            print("🤷‍♂️ 当前没有可领取的任务。")
            # 如果你希望“没有任务”也算作一种不需要报警的正常状态，就不要加 sys.exit(1)
            # 保持 exit code 为 0 即可
            return

        for task in tasks:
            run_task(task)
            time.sleep(2)
            
        print("\n🏁 所有任务流程结束。")
        
    except Exception as e:
        print(f"❌ 发生未捕获的异常: {e}")
        sys.exit(1) # <--- 兜底捕获，确保未知错误也会报警

if __name__ == "__main__":
    main()