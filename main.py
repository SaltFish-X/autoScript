import requests
import json
import time
import os
import sys

def start_checkin():
    # 1. 从环境变量获取机密信息 (GitHub Secrets)
    # 如果在本地运行，你需要手动设置这些环境变量，或者暂时改回写死的方式测试
    cookie_val = os.environ.get("GEMAI_COOKIE")
    user_id = os.environ.get("GEMAI_USER")

    if not cookie_val or not user_id:
        print("❌ 错误：未检测到环境变量。请在 GitHub Settings -> Secrets 中配置 GEMAI_COOKIE 和 GEMAI_USER")
        sys.exit(1) # 终止运行

    # 2. 接口地址
    url = "https://api.gemai.cc/api/user/checkin"

    # 3. 构造 Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Cookie": cookie_val,     # 这里的变量来自环境变量
        "new-api-user": user_id   # 这里的变量来自环境变量
    }

    # 4. 构造请求体
    data = {}

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在请求签到接口...")

    try:
        response = requests.post(url=url, headers=headers, json=data)
        print("状态码:", response.status_code)
        
        try:
            res_json = response.json()
            print("返回结果:", json.dumps(res_json, ensure_ascii=False, indent=2))
            
            # 根据返回结果判断是否成功 (假设 code 0 或 200 为成功，需根据实际情况调整)
            if response.status_code == 200:
                print("✅ 脚本执行完毕")
            else:
                print("❌ 签到可能失败，请检查日志")
                # 这里可以让 GitHub Action 报错，方便你收到邮件通知
                sys.exit(1)
                
        except json.JSONDecodeError:
            print("❌ 返回的不是 JSON 数据:", response.text)

    except Exception as e:
        print(f"🚫 请求发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_checkin()