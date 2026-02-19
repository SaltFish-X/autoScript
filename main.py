import requests
import json
import time
import os
import sys

# 使用 Session 自动管理 Cookie
session = requests.Session()

def get_credentials():
    """
    获取账号密码逻辑：
    1. 优先从环境变量获取 (GitHub Actions)
    2. 其次从本地 config.json 获取 (本地调试)
    """
    user = os.environ.get("GEMAI_USERNAME")
    pwd = os.environ.get("GEMAI_PASSWORD")

    if user and pwd:
        print("✅ 检测到环境变量，使用远程模式运行。")
        return user.strip(), pwd.strip()

    # 尝试从本地文件获取
    local_file = "config.json"
    if os.path.exists(local_file):
        try:
            with open(local_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                user = config.get("username")
                pwd = config.get("password")
                if user and pwd:
                    print(f"✅ 检测到本地文件 {local_file}，使用本地模式运行。")
                    return user.strip(), pwd.strip()
        except Exception as e:
            print(f"⚠️ 读取本地文件失败: {e}")

    return None, None

def login(username, password):
    """登录获取 Session 和 UserID"""
    login_url = "https://api.gemai.cc/api/user/login?turnstile="
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Referer": "https://gemai.cc/"
    }
    
    payload = {
        "username": username,
        "password": password
    }

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在尝试登录账户: {username}...")
    
    try:
        response = session.post(login_url, headers=headers, json=payload, timeout=20)
        
        if response.status_code != 200:
            print(f"❌ 登录接口请求失败，状态码: {response.status_code}")
            sys.exit(1) # 触发邮件提醒

        res_json = response.json()
        
        # 判断登录是否成功的逻辑
        if res_json.get("code") in [200, 0] or "data" in res_json:
            print("✅ 登录成功！")
            # 提取 UserID，用于签到 Header
            user_id = res_json.get("data", {}).get("id") or res_json.get("id")
            return str(user_id) if user_id else ""
        else:
            print(f"❌ 登录失败，原因: {res_json.get('message', '未知错误')}")
            sys.exit(1) # 触发邮件提醒

    except Exception as e:
        print(f"🚫 登录过程发生崩溃: {e}")
        sys.exit(1)

def start_checkin(user_id):
    """执行签到"""
    url = "https://api.gemai.cc/api/user/checkin"
    
    checkin_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }
    
    if user_id:
        checkin_headers["new-api-user"] = user_id

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在请求签到接口...")

    try:
        response = session.post(url, headers=checkin_headers, json={}, timeout=20)
        res_json = response.json()
        
        print(f"状态码: {response.status_code}")
        print("返回结果:", json.dumps(res_json, ensure_ascii=False, indent=2))
        
        if response.status_code == 200:
            msg = res_json.get("message") or res_json.get("msg") or ""
            # 常见成功提示：包含“成功”或“重复”
            if "成功" in msg or "重复" in msg or res_json.get("code") in [200, 0]:
                print("✅ 签到脚本执行完毕")
            else:
                print("❌ 签到业务逻辑返回错误")
                sys.exit(1)
        else:
            print("❌ 签到接口响应异常")
            sys.exit(1)
                
    except Exception as e:
        print(f"🚫 签到请求失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 1. 获取凭据
    username, password = get_credentials()

    if not username or not password:
        print("❌ 错误：未找到账号密码。请配置环境变量或本地 config.json 文件。")
        sys.exit(1)

    # 2. 登录并签到
    uid = login(username, password)
    start_checkin(uid)