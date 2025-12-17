from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

"""
然後打開瀏覽器前往：http://localhost:8000 你就可以在網頁上輸入文字，並看到伺服器即時回應。
"""

app = FastAPI()

# -------------------------
# 1. 前端測試頁面 (HTML)
# -------------------------
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>FastAPI WebSocket 測試</title>
    </head>
    <body>
        <h1>FastAPI WebSocket Echo</h1>
        <input type="text" id="messageText" autocomplete="off"/>
        <button onclick="sendMessage()">傳送</button>
        
        <ul id='messages'>
        </ul>
        
        <script>
            // 建立 WebSocket 連線
            var ws = new WebSocket("ws://localhost:8000/ws");
            
            // 當收到 Server 回傳訊息時
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('li');
                var content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };

            // 傳送訊息給 Server
            function sendMessage() {
                var input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
            }
        </script>
    </body>
</html>
"""

# --- 連線管理器 ---
class ConnectionManager:
    def __init__(self):
        # 這裡用一個 List 存所有連上來的 user
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        # 傳給特定的人
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        # 廣播給所有人
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- 修改後的 Endpoint ---
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    # 連線時加入名單
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 收到某人的訊息，廣播給所有人：「Client #1 說：Hello」
            await manager.broadcast(f"Client #{client_id} 說: {data}")
            
    except WebSocketDisconnect:
        # 斷線時移除名單，並通知其他人
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} 離開了聊天室")