import asyncio
import inspect
import random
import time
import asyncmy
from types import SimpleNamespace
from config_api import (MYSQL_DB, MYSQL_HOST, MYSQL_MAXSIZE, MYSQL_MINSIZE,
                            MYSQL_PASSWD, MYSQL_PORT, MYSQL_USER)

# 設置行緩衝，適合背景執行
sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), "w", 1)

# 全域終止訊號
terminate_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --------------------------------------------------------------------------
    # 階段一：應用程式啟動與資源初始化
    # --------------------------------------------------------------------------
    try:
        def_name = inspect.currentframe().f_code.co_name
    except Exception as e:
        def_name = "lifespan"
        print(def_name, "獲取方法名稱失敗", str(e))

    target_delay = 5  # 每次重試間隔時間（秒）
    poll_interval = 1  # 輪詢間隔時間（秒）

    redis_client = mysql_pool = mq_conn = es_client = None

    # 初始化 MySQL 連接池
    attempt = 0
    while not terminate_event.is_set():  # 無限循環，直到成功或收到終止信號
        try:
            mysql_pool = await asyncmy.create_pool(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWD,
                db=MYSQL_DB,
                charset="utf8mb4",
                autocommit=True,
                minsize=MYSQL_SIZE_MIN,
                maxsize=MYSQL_SIZE_MAX,
            )
            print(def_name, "MySQL 連接成功")
            break

        except Exception as e:
            attempt += 1
            print(f"MySQL 連接失敗，第 {attempt} 次嘗試，{str(e)}")

            # 每秒鐘檢查一次 terminate_event
            for _ in range(target_delay):
                if terminate_event.is_set():
                    break
                await asyncio.sleep(poll_interval)

    # 將 mysql_pool 資源和管理器加入 FastAPI 應用狀態       
    app.state.mysql = mysql_pool

    #API 使用統計或監控
    app.state.api_stats = {
    "總請求數": 0, "各端點請求數": {}, "平均處理時間": 0.0, "當前活躍請求數": 0,
    }  

    print(f"啟動完成")

    # --------------------------------------------------------------------------
    # 階段二：定義並啟動所有背景任務
    # --------------------------------------------------------------------------
    # 創建處理鎖
    app.state.processing_lock = Lock()

    # 定期檢查連接池狀態
    async def check_pool_status():
        while not terminate_event.is_set():
            # 初始化或獲取歷史最高值，如果不存在就設定為 0
            app.state.mysql_highest_size = getattr(app.state, 'mysql_highest_size', 0)
            app.state.mq_highest_queue_length = getattr(app.state, 'mq_highest_queue_length', 0)
            app.state.mq_highest_consumer_count = getattr(app.state, 'mq_highest_consumer_count', 0)
            # 預設隊列長度與消費者數量
            queue_length = 0 # 預設值
            consumer_count = 0 # 預設值

            # 監控 MySQL 連接池
            if hasattr(app.state, 'mysql') and app.state.mysql:
                # 更新歷史最大連接數
                app.state.mysql_highest_size = max(app.state.mysql_highest_size, app.state.mysql.size)
                # 當前連接數
                mysql_conn_size = app.state.mysql.size
            else:
                mysql_conn_size = "N/A"

            # 封裝所有狀態
            db_status = {
                "MySQL連接池(當前/歷史/最小/最大)": f"{mysql_conn_size}/{getattr(app.state, 'mysql_highest_size', 'N/A')}/{MYSQL_SIZE_MIN}/{MYSQL_SIZE_MAX}",
            }
            combined_status = {"資料庫狀態": db_status}
            # 存入 app.state，方便其他地方讀取
            app.state.db_status = db_status 
            print("check_pool_status","檢查連接池狀態", combined_status)

            # 延遲 60 秒再檢查一次
            for _ in range(60):
                if terminate_event.is_set():  # 如果程式關閉，退出循環
                    return
                await asyncio.sleep(1)

    # 啟動所有背景任務並統一管理
    background_tasks = [
        asyncio.create_task(check_pool_status()),

    ]
    app.state.background_tasks = background_tasks
    print(def_name, "所有資源初始化完成，背景任務已啟動", f"共 {len(background_tasks)} 項")   

    try:
        yield  # 應用程式在此處運行
    finally:
        # 輸出關閉訊息
        print("lifespan.shutdown: 應用程式準備關閉，開始清理資源...")
        terminate_event.set()

        # 優雅地取消所有背景任務
        for task in app.state.background_tasks:
            task.cancel()
        await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
        print("lifespan.shutdown: 所有背景任務已成功取消")

        # 清理 MySQL 連接池
        if hasattr(app.state, 'mysql') and app.state.mysql:
            try:
                print("應用結束", "開始釋放 MySQL 連接", "")
                app.state.mysql.close()
                await app.state.mysql.wait_closed()
                print("應用結束", "釋放 MySQL 連接成功", "")
            except Exception as e:
                print("應用結束", "釋放 MySQL 連接失敗", str(e))
            finally:
                app.state.mysql = None  # 標記為已關閉

        print(f"服務已關閉")

app = FastAPI(lifespan=lifespan)
# 解決跨域問題
origins = ["*"]
# 設置跨域傳參數允許所有來源
app.add_middleware(
    CORSMiddleware,  #處理跨域請求
    allow_origins=origins,  # 設置允許的origins來源
    allow_credentials=True,
    allow_methods=["*"],  # 設置允許跨域的http方法，比如 get、post、put等。
    allow_headers=["*"],
)  # 允許跨域的headers，可以用來鑒別來源等作用。

# -----------------------------------------------------------------------------
# 核心函數 (Core Functions)
# -----------------------------------------------------------------------------

# 通用的資料庫操作函數
async def mysql_exec(
    from_where=None,  # 來源/調用API名稱，用於日誌記錄
    select_query=None,  # SELECT 查詢語句 (字串)
    select_params=None,  # SELECT 查詢參數 (元組或列表)
    fetch_method="one",  # 查詢結果獲取方式: "one" (一條) 或 "all" (全部)
    update_queries=None,  # UPDATE/INSERT/DELETE 查詢語句列表 (字串列表)
    update_params_list=None,  # UPDATE/INSERT/DELETE 查詢參數列表 (列表的列表/元組)
    lock=False,  # 是否開啟事務 (START TRANSACTION 和 COMMIT/ROLLBACK)
    use_executemany=False,  # 是否使用 executemany 批量執行更新
    conn=None,  # 可選: 預先存在的連接對象
    cur=None,  # 可選: 預先存在的游標對象
):
    try:
        def_name = inspect.currentframe().f_code.co_name
    except Exception as e:
        def_name = "mysql_exec"
        await logsys(9, def_name, "獲取方法名稱失敗", str(e))

    max_retries = 3  # 最大重試次數
    retry_delay = 0.5  # 初始延遲時間
    exponential_base = 1.5  # 指數基數
    error_codes_to_retry = {1213, 1205, 2006, 2013}  # 需要重試的錯誤碼
    retries = 0
    total_wait_time = 0

    mysql_pool = app.state.mysql

    # 標記變數：判斷連線是這裡建立的，還是外面傳進來的
    # 如果 conn 是 None，代表我們要自己建立，那麼這個函數就有責任在失敗時清理它
    created_new_connection = False 

    while (
        retries < max_retries and total_wait_time < 30 and not terminate_event.is_set()
    ):
        start_time = time.perf_counter()  # 記錄本次嘗試的開始時間
        if conn is None or cur is None:
            conn = await mysql_pool.acquire()
            # 標記：這是我借的，我有責任還
            created_new_connection = True 
            
            # 動態導入 DictCursor
            dict_cursor = getattr(asyncmy.cursors, "DictCursor")
            cur = conn.cursor(dict_cursor)
            
        try:
            if lock:
                await cur.execute("START TRANSACTION")
            select_result = None
            # 執行 SELECT 查詢
            if select_query:
                # 如果查詢包含 "FOR UPDATE"，則禁用自動提交
                if "FOR UPDATE" in select_query.upper():
                    await conn.autocommit(False)
                await cur.execute(select_query, select_params)
                if fetch_method == "one":
                    select_result = await cur.fetchone()
                elif fetch_method == "all":
                    select_result = await cur.fetchall()
                else:
                    raise ValueError("無效的 fetch_method,請使用 'one' 或 'all'。")

            # 執行更新 (UPDATE/INSERT/DELETE) 操作
            if update_queries and update_params_list:
                if use_executemany:
                    # 使用 executemany 批量執行單個查詢語句的多組參數
                    await cur.executemany(update_queries, update_params_list)
                    rowcount = cur.rowcount
                    await logsys(
                        0,
                        def_name,
                        f"執行更新: {update_queries}, 參數: {update_params_list}, 影響行數: {rowcount}",
                        f"調用API: {from_where}"
                    )
                    select_result = rowcount  # 將影響行數作為結果返回
                else:
                    # 逐個執行多個查詢語句
                    for update_query, update_params in zip(
                        update_queries, update_params_list
                    ):
                        await cur.execute(update_query, update_params)
                        rowcount = cur.rowcount
                        await logsys(
                            0,
                            def_name,
                            f"執行更新: {update_query}, 參數: {update_params}, 影響行數: {rowcount}",
                            f"調用API: {from_where}"
                        )
                        select_result = rowcount  # 將最後一個查詢的影響行數作為結果返回

            # 如果 lock 為 True，則提交事務
            if lock:
                await cur.execute("COMMIT")
            # 成功時，連線的所有權轉移給 Return 值，這裡不釋放
            return select_result, conn, cur
        except Exception as e:
            # 動態導入 MySQLError
            mysql_error = getattr(asyncmy.errors, "MySQLError")
            # Rollback 嘗試
            if lock and conn:
                try:
                    await cur.execute("ROLLBACK")
                except Exception:
                    pass # Rollback 失敗通常是因為連線已經斷了，忽略即可
            end_time = time.perf_counter()
            actual_run_time = end_time - start_time
            if isinstance(e, mysql_error):
                await logsys(
                    99,
                    def_name,
                    f"第{retries + 1}次重試實際運行時間:{actual_run_time:.2f}秒",
                    f"查詢失敗: {str(e)}, 錯誤碼: {e.args[0]}, 調用API: {from_where}, 查詢: {select_query}, 參數: {select_params}, 更新: {update_queries}, 參數: {update_params_list}"
                )
                # 情境 A: 可重試的錯誤 (Deadlock 等)
                if e.args[0] in error_codes_to_retry:
                    retries += 1
                    # 指數退避計算等待時間，並加上隨機抖動 (Jitter)
                    wait_time = retry_delay * (
                        exponential_base**retries
                    ) + random.uniform(0, retry_delay * 2)
                    total_wait_time += wait_time
                    await logsys(
                        0,
                        def_name,
                        f"檢測到錯誤 {e.args[0]}。重試 {retries}/{max_retries} 次... 等待{wait_time:.2f}秒",
                        f"調用API: {from_where}, 查詢: {select_query}, 參數: {select_params}, 更新: {update_queries}, 參數: {update_params_list}"
                    )
                    if e.args[0] in {2006, 2013}:
                        # 連線斷了，無論是誰建立的，都需要清理舊的物件，因為下一輪會建立新的
                        if cur:
                            try: await cur.close()
                            except Exception: pass
                        if conn:
                            # 這裡要小心：如果是外部傳入的conn斷了，我們 release 它；
                            # 下一輪我們會建立新的，這時候 created_new_connection 會在下一輪變成 True
                            try: await mysql_pool.release(conn)
                            except Exception: pass
                        conn = None 
                        cur = None
                    await asyncio.wait(
                        [
                            asyncio.create_task(terminate_event.wait()),
                            asyncio.create_task(asyncio.sleep(wait_time)),
                        ],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                # 情境 B: 不可重試的錯誤 (Data too long, Syntax error 等)
                else:
                    await logsys(
                        9,
                        def_name,
                        f"執行查詢或更新失敗 (不可重試): {str(e)}",
                        f"調用API: {from_where}, 查詢: {select_query}, 參數: {select_params}, 更新: {update_queries}, 參數: {update_params_list}"
                    )
                    # 只有當連線是我們自己建立的時候，我們才在報錯前釋放它
                    # 如果是外部傳入的，外部的 finally 會負責釋放
                    if created_new_connection:
                        if cur:
                            try: await cur.close()
                            except Exception: pass
                        if conn:
                            try: await mysql_pool.release(conn)
                            except Exception: pass
                    raise e
            else:
                # 情境 C: 非 MySQL 錯誤 (Python 代碼錯誤等)
                await logsys(
                    9,
                    def_name,
                    f"未知錯誤: {str(e)}",
                    f"調用API: {from_where}, 查詢: {select_query}, 參數: {select_params}, 更新: {update_queries}, 參數: {update_params_list}"
                )
                # 同樣，只有我們建立的才釋放
                if created_new_connection:
                    if cur:
                        try: await cur.close()
                        except Exception: pass
                    if conn:
                        try: await mysql_pool.release(conn)
                        except Exception: pass
                
                raise e
        finally:
            # 處理 Loop 結束但未 Return 的情況 (例如重試次數用盡)
            if retries >= max_retries or terminate_event.is_set():
                # 確保只清理我們自己建立的資源
                if created_new_connection:
                    if cur is not None:
                        try: await cur.close()
                        except Exception: pass
                    if conn is not None:
                        try: await mysql_pool.release(conn)
                        except Exception: pass
    # 退出循環 (達到最大重試次數或收到終止信號)，拋出異常
    raise Exception("達到最大重試次數或收到終止信號")


# 重置連接狀態並釋放回連接池
async def reset_connection(conn):
    try:
        def_name = inspect.currentframe().f_code.co_name
    except Exception as e:
        def_name = "reset_connection"
        await logsys(9, def_name, "獲取方法名稱失敗", str(e))
    try:
        await conn.autocommit(True)  #嘗試將連接的 autocommit 模式設置回 True
    except Exception as e:  
        await logsys(9, def_name, "重置連線時出錯", str(e))  # 記錄日誌但不重新拋出異常。
    finally:
        app.state.mysql.release(conn)  # 無論 autocommit 重置是否成功，都必須將連接釋放回連接池。


