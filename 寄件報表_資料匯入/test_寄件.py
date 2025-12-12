import asyncio
import os
import sys
import aiohttp  # 現代 Python 網頁請求標準庫 (需 pip install aiohttp)
from datetime import datetime

# 設置行緩衝
sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), "w", 1)

# ==========================================
# 1. 全局配置區域 (Configuration)
# ==========================================
TOOL_VERSION = '0.08'
PROGRAM_NAME = '米匯寶-寄件報表程式'
WINDOW_TITLE = f'{PROGRAM_NAME} Ver {TOOL_VERSION}'
REMARK = '主要更新：add boncpu.cc'

# 取得程式所在目錄的絕對路徑 (用於檔案路徑強健性)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 商城列表 (將由 domain.txt 載入)
HOST_API_LIST = []

def load_domains(filename='domain.txt'):
    """從檔案載入網域列表"""
    # 取得程式所在目錄的絕對路徑
    base_dir = SCRIPT_DIR
    file_path = os.path.join(base_dir, filename)

    domains = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
            print(f"[系統] 已從 {filename} 載入 {len(domains)} 個網域。")
        except Exception as e:
            print(f"[錯誤] 讀取網域設定檔失敗: {e}")
    else:
        print(f"[警告] 找不到 {file_path}，請確保檔案存在。")
    return domains

# 初始化載入
HOST_API_LIST = load_domains()

# API 密鑰與參數
E5_PASSWD = '2d6um@fZ.?=Q8qF7SS6seaW?QP3d!?!T'

# ==========================================
# 2. 工具函式 (Utilities)
# ==========================================
def clear_screen():
    """清除螢幕，支援 Windows 與 Linux/Mac"""
    os.system('cls' if os.name == 'nt' else 'clear')


async def get_input(prompt: str) -> str:
    """
    非阻塞輸入函式
    在 asyncio 架構下，使用 executor 避免 input() 卡住整個程式的事件迴圈
    """
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt)

# ==========================================
# 3. 核心邏輯 (Core Logic)
# ==========================================
def show_menu():
    """顯示選單介面"""
    clear_screen()
    print(WINDOW_TITLE)
    print(REMARK)
    print('-' * 30)
    for index, domain in enumerate(HOST_API_LIST):
        print(f"{index + 1}. 取得資料: {domain}")
    print("0. 結 束 程 式")
    print('-' * 30)


async def download_report(session: aiohttp.ClientSession, select_mall_idx: int, e5_date: str) -> bool:
    """
    執行下載報表的任務
    回傳: True (成功), False (失敗)
    """
    try:
        domain = HOST_API_LIST[select_mall_idx]
        url = f'https://apiinternal.{domain}/get_ship_info'
        
        # 參數設置
        params = {
            'e5_passwd': E5_PASSWD,
            'e5_date': e5_date
        }

        print(f"[系統] 正在連線至: {domain} ...")
        
        # 使用 aiohttp 發送非同步 GET 請求
        async with session.get(url, params=params, timeout=30) as response:
            if response.status != 200:
                print(f"[錯誤] HTTP 狀態碼異常: {response.status}")
                return False

            # 讀取內容
            content = await response.read()
            filename = f'寄件報表-{domain}.xls'

            # 寫入檔案
            with open(filename, mode='wb') as f:
                f.write(content)
            
            print(f"[成功] 檔案已儲存: {filename}")
            return True

    except aiohttp.ClientError as e:
        print(f"[連線錯誤] 無法連接伺服器: {e}")
        return False
    except Exception as e:
        print(f"[系統錯誤] 發生未預期錯誤: {e}")
        return False


async def process_shipping_task(choice: int, session: aiohttp.ClientSession):
    """
    處理寄件報表匯出的單一任務邏輯
    包含：範圍檢查、詢問日期、呼叫下載、結果顯示
    """
    # 1. 範圍檢核
    if not (1 <= choice <= len(HOST_API_LIST)):
        print("[提示] 選項無效，請重新輸入。")
        await asyncio.sleep(1)
        return

    # 2. 準備參數
    target_mall_idx = choice - 1
    target_domain = HOST_API_LIST[target_mall_idx]
    print(f"已選擇: {target_domain}")
    
    try:
        # 3. 輸入日期 (這是任務的一部分，所以在這邊詢問)
        date_input = await get_input('請輸入您欲匯出的日期 (今天不輸入，前一天1，前兩天2，以此類推...): ')
        
        # 4. 執行下載
        is_success = await download_report(session, target_mall_idx, date_input)
        
        # 5. 顯示結果
        print("-" * 30)
        print("匯出完畢" if is_success else "發生錯誤")
        await get_input('請按 Enter 鍵返回主選單...')

    except Exception as e:
        print(f"[任務錯誤] 處理過程發生異常: {str(e)}")
        await get_input('按任意鍵繼續...')

# ==========================================
# 4. 主程式入口 (Entry Point)
# ==========================================
async def main():
    """主選單"""
    print(f"[啟動] {PROGRAM_NAME} 正在初始化...")
    
    # 使用 aiohttp 建立一個共用的 Session
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # 1. 顯示選單
                show_menu()
                
                # 2. 獲取使用者輸入
                choice_str = await get_input('請輸入您的選擇: ')
                
                # 3. 驗證輸入
                if not choice_str.isdigit():
                    print("[提示] 輸入錯誤，請輸入數字。")
                    await asyncio.sleep(1)
                    continue
                
                choice = int(choice_str)

                # 4. 處理邏輯
                if choice == 0:
                    print("[系統] 程式結束。")
                    break
                
                # 呼叫任務處理函式 (將邏輯轉發出去)
                await process_shipping_task(choice, session)
                
            except KeyboardInterrupt:
                print("\n[系統] 使用者強制中斷程式 (Ctrl+C)")
                break
            except Exception as e:
                print(f"\n[致命錯誤] 主迴圈錯誤: {str(e)}")
                await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        # Windows 平台下的 Event Loop 策略修正 (Python 3.8+ 在 Windows 上的 asyncio 限制)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        # 啟動非同步主程式
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n[系統] 使用者強制中斷程式 (Ctrl+C)")
    except Exception as e:
        print(f"\n[致命錯誤] 程式崩潰: {e}")
        input("按 Enter 鍵離開...")