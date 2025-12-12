import asyncio
import os
import json
import sys
import traceback
import aiohttp

# 設置行緩衝
sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), "w", 1)

# ============================================ 
# 1. 全局配置區域 (Configuration)
# ============================================ 
TOOL_VERSION = '0.24'
PROGRAM_NAME = '米匯寶-資料匯入程式'
WINDOW_TITLE = f'{PROGRAM_NAME} Ver {TOOL_VERSION}'
REMARK = '主要更新：add boncpu.cc'

# 取得程式所在目錄的絕對路徑 (用於檔案路徑強健性)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# API Host 列表 (將由 domain.txt 載入)
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

# 密碼設定
PWD_QUERY_PENDING = '9=Hev%wZmtR9fFaGXxWq+cWdf+h$GWQk'
PWD_IMPORT_ACTION = 'SbT?.%23mkMKp8D5qy6mk?vhzc9%23Y4uhFy'
PWD_PURCHASE_ACTION = 'LSldRLRo5VzucUV9YxMBCJ490vw3PfQs1XVpGmTJ'

# 檔案名稱對應
FILE_MAP = {
    'address': '1.txt',
    'order': '2.txt',
    'purchase': '3.txt'
}

# ============================================ 
# 2. 工具函式 (Utilities)
# ============================================ 
def clear_screen():
    """清除螢幕，支援 Windows 與 Linux/Mac"""
    os.system('cls' if os.name == 'nt' else 'clear')


async def get_input(prompt: str) -> str:
    """
    非阻塞輸入函式
    在 asyncio 架構下，使用 executor 避免 input() 卡住整個程式的事件迴圈
    """
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt)

# ============================================ 
# 3. 核心邏輯 (Core Logic)
# ============================================ 
def show_menu():
    """顯示選單介面"""
    clear_screen()
    print(WINDOW_TITLE)
    print(REMARK)
    print('-' * 30)
    
    cnt = 1
    action_types = ["匯入地址", "匯入訂單", "匯入採購單"]

    for action_type in action_types:
        for host in HOST_API_LIST:
            print(f"{cnt}.{action_type}: {host}")
            cnt += 1
        print('=' * 30)
        
    print('0.結 束 程 式')
    print('-' * 30)


async def process_import_task(select_mall: int, session: aiohttp.ClientSession):
    """處理匯入邏輯"""
    list_len = len(HOST_API_LIST)
    if list_len == 0:
        print("[錯誤] 尚未載入任何網域，無法執行操作。")
        await get_input('按 Enter 鍵返回...')
        return

    # 0. 基礎檢核
    if select_mall < 1 or select_mall > 3 * list_len:
        print("無效的選項")
        await asyncio.sleep(1)
        return

    # 1. 共通邏輯：計算並顯示商城
    # 利用餘數計算索引 (例如 1, 17, 33 對應同一個 host)
    idx = (select_mall - 1) % list_len
    target_host = HOST_API_LIST[idx]
    # print(f'選擇的商城: {target_host}') # Moved to after URL construction

    file_name = ""
    endpoint = ""
    current_password = PWD_IMPORT_ACTION # 預設為 PWD_IMPORT_ACTION
    
    # 2. 分歧邏輯：設定檔案、端點與執行特殊檢查
    try:
        # === 匯入地址 (選項 1 ~ 16) ===
        if select_mall <= list_len:
            file_name = FILE_MAP['address']
            endpoint = '/import_address'

            # 驗證剩餘單數 (地址匯入特有邏輯)
            check_url = f'https://apiinternal.{target_host}/query_pending_orders'
            postbody = {'d1_password': PWD_QUERY_PENDING}
            
            print(f'正在連線驗證: {check_url} ...')
            try:
                # 設定 headers 確保 json 傳輸正確
                headers = {'Content-Type': 'application/json'}
                async with session.post(check_url, json=postbody, headers=headers, timeout=600) as response:
                    resp_text = await response.text()
                    print(f'檢查回應文字: {resp_text}')
                    print(f'檢查狀態碼: {response.status}')
                    try:
                        resp_json = json.loads(resp_text)
                        if str(resp_json.get('data')) != '0':
                            print(f'錯誤! 米匯寶-匯入地址資料程式-剩餘單數不為0! 剩餘單數: {resp_text}')
                            await get_input('請確認錯誤(匯入地址)')
                            return
                    except json.JSONDecodeError:
                        print(f'錯誤! 回傳格式異常: {resp_text}')
                        return

            except Exception as e:
                print(f"驗證API失敗: {str(e)}")
                await get_input('請確認錯誤(驗證階段)')
                return

        # === 匯入訂單 (選項 17 ~ 32) ===
        elif select_mall <= 2 * list_len:
            file_name = FILE_MAP['order']
            endpoint = '/f7_import_order'

        # === 匯入採購單 (選項 33 ~ 48) ===
        else:
            file_name = FILE_MAP['purchase']
            endpoint = '/f9_import_purorder'
            current_password = PWD_PURCHASE_ACTION # 採購單使用專屬密碼

        # 3. 統一組裝 API URL
        api_url = f'https://apiinternal.{target_host}{endpoint}?password={current_password}'
        print(f'選擇的商城: {target_host} URL: {api_url}')

        # 4. 執行檔案上傳
        full_file_path = os.path.join(SCRIPT_DIR, file_name)
        if not os.path.exists(full_file_path):
            print(f"錯誤! 找不到檔案: {full_file_path}")
            await get_input('請確認檔案是否存在')
            return

        print('資料處理中，請勿做其他動作。')
        
        try:
            # 讀取檔案並上傳
            data = aiohttp.FormData()
            # 注意: 這裡使用 with open 確保檔案在上傳後正確關閉
            with open(full_file_path, 'rb') as f:
                data.add_field('file', f, filename=file_name, content_type='text/plain')
                
                async with session.post(api_url, data=data, timeout=10) as response:
                    resp_text = await response.text()
                    if response.status == 200:
                        print("上傳成功")
                        print(f"響應資訊: {resp_text}")
                    else:
                        print(f"上傳失敗 HTTP {response.status} - 響應資訊:{resp_text}")
                        
        except Exception as e:
            print(f'錯誤! 處理失敗! {str(e)}')
            await get_input('請確認錯誤')
            return

        await get_input('匯入完畢,請按任意鍵返回主選單')

    except Exception as e:
        traceback.print_exc()
        print(f"發生未預期錯誤: {str(e)}")
        await get_input('按任意鍵繼續...')

# ============================================ 
# 4. 主程式入口 (Entry Point)
# ============================================ 
async def main():
    # 建立一個長效連接 session
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                show_menu()
                print(f'匯入地址的檔案命名為 {FILE_MAP["address"]}')
                print(f'匯入訂單的檔案命名為 {FILE_MAP["order"]}')
                print(f'匯入採購單的檔案命名為 {FILE_MAP["purchase"]}')
                print('請將欲匯入的檔案並放入本程式同目錄下')
                
                user_input = await get_input('請輸入您的選擇: ')
                
                if not user_input.isdigit():
                    print("[提示] 輸入錯誤，請輸入數字。 ")
                    await asyncio.sleep(1)
                    continue
                
                select_mall = int(user_input)
                
                if select_mall == 0:
                    print("程式結束")
                    break
                
                print(f'已選擇: {select_mall}')
                
                # 呼叫處理邏輯
                await process_import_task(select_mall, session)
                
            except KeyboardInterrupt:
                print("\n[系統] 使用者強制中斷程式 (Ctrl+C)")
                break
            except Exception as e:
                print(f"\n[致命錯誤] 主迴圈錯誤: {str(e)}")
                await asyncio.sleep(1)


if __name__ == '__main__':
    # Windows 平台修正
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系統] 使用者強制中斷程式 (Ctrl+C)")
    except Exception as e:
        print(f"\n[致命錯誤] 程式崩潰: {e}")
        input("按 Enter 鍵離開...")
