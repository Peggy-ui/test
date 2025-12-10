import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QLabel, QVBoxLayout, QWidget)

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. 設定主視窗標題與大小
        self.setWindowTitle("PyQt 範例")
        self.setGeometry(100, 100, 300, 200)  # 位置 (x, y)、大小 (width, height)

        # 2. 建立中心 Widget (因為 QMainWindow 需要一個中心容器)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 3. 建立 Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 4. 建立元件 (Label 和 Button)
        self.label = QLabel("尚未點擊")
        self.button = QPushButton("點我")

        # 5. 將元件加入 Layout
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        # 6. 連接 Signal 與 Slot (核心重點)
        # 當按鈕被點擊 (clicked) -> 執行 self.on_button_click 函數
        self.button.clicked.connect(self.on_button_click)

    def on_button_click(self):
        # Slot 函數：更新 Label 文字
        self.label.setText("按鈕已被點擊！")
        self.label.setStyleSheet("color: #FF0080; font-weight: bold;")

if __name__ == "__main__":
    # 建立 Application
    app = QApplication(sys.argv)
    
    # 建立並顯示視窗
    window = MyApp()
    window.show()
    
    # 進入事件迴圈
    sys.exit(app.exec())