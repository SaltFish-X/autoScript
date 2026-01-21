import os
import time
import json
import random
import requests
import sys
import urllib3
from urllib.parse import urlparse, parse_qs

# ================= 修复 SSL 报错区域 =================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ====================================================

# ================= 配置区域 =================

def get_cookie():
    # 1. 尝试从环境变量获取
    cookie = os.environ.get("BAIDU_COOKIE")
    if cookie:
        print("✅ 检测到环境变量 BAIDU_COOKIE，使用远程模式运行。")
        return cookie.strip()

    # 2. 尝试从本地文件获取
    local_file = "cookie_baidu.txt"
    if os.path.exists(local_file):
        print(f"✅ 检测到本地文件 {local_file}，使用本地模式运行。")
        try:
            with open(local_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as e:
            print(f"⚠️ 读取本地文件失败: {e}")

    return None

COOKIE = get_cookie()
if not COOKIE:
    print("❌ 错误：未找到 Cookie！")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://pan.baidu.com/",
    "Origin": "https://pan.baidu.com",
    "Cookie": COOKIE,
    "Content-Type": "application/json"
}

CHANNELS = [10066, 10065]
# 注意：根据你的日志，任务模块名确实是 game_return_play
TARGET_MODULES = ["game_return_play", "new_game_play"] 

def get_task_list():
    """获取任务列表"""
    all_tasks = []
    print("🔄 正在获取任务列表...")
    
    for channel in CHANNELS:
        url = f"https://wan.baidu.com/gameapi?action=bonus_pan_task_list&channel={channel}"
        try:
            res = requests.get(url, headers=HEADERS, verify=False).json()
            
            if res.get("errorNo") == 110008:
                print(f"❌ 获取列表失败：Cookie 已失效，请更新 Secret。")
                sys.exit(1) 

            if res.get("errorNo") == 0 and res.get("result"):
                # 【修改点 1】获取原始数据列表（这是一组组的数据）
                raw_groups = res["result"].get("data", [])
                
                # 【修改点 2】解包嵌套结构
                if isinstance(raw_groups, list):
                    for group in raw_groups:
                        # 如果是新版结构：{'module': 'xxx', 'data': [task1, task2]}
                        if isinstance(group, dict) and "data" in group and isinstance(group["data"], list):
                            all_tasks.extend(group["data"])
                        # 如果是旧版结构：直接就是任务对象（保留兼容性）
                        else:
                            all_tasks.append(group)
                            
        except Exception as e:
            print(f"⚠️ 获取频道 {channel} 失败: {e}")

    unique_tasks = []
    seen_ids = set()
    
    print(f"🔍 初步获取到 {len(all_tasks)} 个原始条目，开始筛选...")

    for t in all_tasks:
        # 调试打印：如果发现还是获取不到，取消下面这行的注释查看数据
        # print(f"DEBUG: taskId={t.get('taskId')} module={t.get('taskModule')}")

        # 筛选模块
        if t.get("taskModule") not in TARGET_MODULES: 
            continue
            
        task_id = t.get("taskId")
        if task_id in seen_ids: continue
        seen_ids.add(task_id)
        
        # 检查是否有游戏链接
        task_games = t.get("taskGames", [])
        if not task_games: continue
        
        game = random.choice(task_games)
        parsed_url = urlparse(game.get("gameUrl", ""))
        params = parse_qs(parsed_url.query)
        
        game_id = params.get('gameId', [None])[0]
        # 优先从 URL 获取 activityId，如果没有则从任务对象获取
        activity_id = params.get('activityId', [None])[0] or t.get("activityId")
        
        if not game_id: continue

        # 【修改点 3】优先读取 taskTitle，其次是 taskName
        task_name = t.get("taskTitle") or t.get("taskName") or "未知任务"

        unique_tasks.append({
            "name": task_name,
            "taskId": task_id,
            "gameId": game_id,
            "activityId": activity_id,
            "totalTime": t.get("eachTaskNeedPlayTimeSecs", 60)
        })
        
    print(f"✅ 筛选完成，共找到 {len(unique_tasks)} 个可执行任务。")
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
            res = requests.get("https://wan.baidu.com/gameapi", params=params, headers=HEADERS, verify=False).json()
            error_no = res.get("errorNo")
            
            if error_no == 0 or error_no == 110503:
                data = res.get("result", {}).get("data", {})
                if error_no == 110503 or data.get("remainingTaskTime", 1) == 0:
                    print(f"🎉 任务 [{task['name']}] 已完成！")
                    return
                remaining_time = data.get("remainingTaskTime", remaining_time)
                print(f"⏳ [{task['name']}] 进行中... 剩余时间: {remaining_time}秒")
                
            elif error_no == 110008:
                print(f"❌ 严重错误：Cookie 已失效/未登录！")
                sys.exit(1)
            else:
                print(f"⚠️ 异常状态码: {error_no}, 信息: {res}")
                if not is_first: return 

            is_first = False
            time.sleep(11) 
            
        except Exception as e:
            print(f"❌ 网络请求错误: {e}")
            return

def main():
    try:
        tasks = get_task_list()
        
        if not tasks:
            print("🤷‍♂️ 当前没有可领取的任务。")
            return

        for task in tasks:
            run_task(task)
            time.sleep(2)
            
        print("\n🏁 所有任务流程结束。")
        
    except Exception as e:
        print(f"❌ 发生未捕获的异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()