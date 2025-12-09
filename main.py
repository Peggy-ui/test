from PyQt5 import QtCore, QtWidgets, QtGui  # 確保從 QtGui 導入
import winsound
import platform
import sys
from plyer import notification
from datetime import datetime, timedelta


class TimerWidget(QtWidgets.QFrame):
    """初始化計時器小部件"""
    def __init__(self, timer_id, remove_callback, sound_var, notify_var):
        super().__init__()
        self.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)  # 設置框架樣式 ，Panel | Raised 3D 凸起效果）
        self.setLineWidth(2)  # 設置框架邊框粗細
        self.setFixedSize(350, 180)  # 設置框架大小

        self.timer_id = timer_id  # 設置計時器ID
        self.is_running = False  # 設置計時器狀態
        self.remaining_time = 0  # 設置剩餘時間
        self.end_time = None  # 設置到期時間
        self.remove_callback = remove_callback  # 設置刪除回調
        self.sound_var = sound_var  # 設置音效變數
        self.notify_var = notify_var  # 設置通知變數
        self.flashing = False  # 設置閃爍狀態

        self.init_ui()
        self.timer = QtCore.QTimer()  # 初始化計時器
        self.timer.timeout.connect(self.update_timer)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(5)  # 設置佈局間距
        layout.setContentsMargins(5, 5, 5, 5)  # 設置佈局邊距

        # 頂部佈局和刪除按鈕
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(5)

        self.id_label = QtWidgets.QLabel(f"計時器 {self.timer_id}")  # 設置ID標籤
        top_layout.addWidget(self.id_label)

        self.remove_button = QtWidgets.QPushButton("X")  # 設置刪除按鈕
        self.remove_button.setFixedWidth(30)
        self.remove_button.clicked.connect(self.remove_timer)
        top_layout.addWidget(self.remove_button)

        layout.addLayout(top_layout)

        # Minute input
        minute_layout = QtWidgets.QHBoxLayout()
        minute_layout.setSpacing(5)

        self.time_label = QtWidgets.QLabel("分鐘:")  # 設置分鐘標籤
        minute_layout.addWidget(self.time_label)

        self.time_entry = QtWidgets.QLineEdit()  # 設置分鐘輸入框
        self.time_entry.setAlignment(QtCore.Qt.AlignLeft)
        minute_layout.addWidget(self.time_entry)

        layout.addLayout(minute_layout)

        # Note input
        note_layout = QtWidgets.QHBoxLayout()
        note_layout.setSpacing(5)

        self.note_label = QtWidgets.QLabel("備註:")  # 設置備註標籤
        note_layout.addWidget(self.note_label)

        self.note_entry = QtWidgets.QLineEdit()  # 設置備註輸入框
        self.note_entry.setAlignment(QtCore.Qt.AlignLeft)
        note_layout.addWidget(self.note_entry)

        layout.addLayout(note_layout)

        # Progress bar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        # Remaining time and end time on the same line
        time_layout = QtWidgets.QHBoxLayout()
        time_layout.setSpacing(5)

        self.remaining_time_label = QtWidgets.QLabel("剩餘時間: 00:00:00")
        time_layout.addWidget(self.remaining_time_label)

        self.end_time_label = QtWidgets.QLabel("到期時間: --:--:--")
        time_layout.addWidget(self.end_time_label)

        layout.addLayout(time_layout)

        # Bottom buttons
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setSpacing(5)

        self.start_button = QtWidgets.QPushButton("開始")
        self.start_button.clicked.connect(self.start_timer)
        bottom_layout.addWidget(self.start_button)

        self.cancel_button = QtWidgets.QPushButton("取消")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_timer)
        bottom_layout.addWidget(self.cancel_button)

        self.reset_button = QtWidgets.QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_timer)
        bottom_layout.addWidget(self.reset_button)

        layout.addLayout(bottom_layout)

    def start_timer(self):
        self.cancel_flash()
        try:
            minutes = float(self.time_entry.text())
            self.remaining_time = int(minutes * 60)
            self.progress.setMaximum(self.remaining_time)
            self.end_time = datetime.now() + timedelta(seconds=self.remaining_time)
            self.update_end_time_label()
        except ValueError:
            QtWidgets.QMessageBox.critical(self, "錯誤", "請輸入有效的分鐘數")
            return

        if self.remaining_time <= 0:
            QtWidgets.QMessageBox.critical(self, "錯誤", "請輸入正的分鐘數")
            return

        self.is_running = True
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.timer.start(1000)

    def update_timer(self):
        if self.is_running and self.remaining_time > 0:
            self.remaining_time -= 1
            self.progress.setValue(self.progress.maximum() - self.remaining_time)
            self.update_remaining_time_label()
        elif self.remaining_time == 0:
            self.time_up()

    def update_remaining_time_label(self):
        hours, remainder = divmod(self.remaining_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.remaining_time_label.setText(f"剩餘時間: {hours:02}:{minutes:02}:{seconds:02}")

    def update_end_time_label(self):
        if self.end_time:
            self.end_time_label.setText(f"到期時間: {self.end_time.strftime('%H:%M:%S')}")
        else:
            self.end_time_label.setText("到期時間: --:--:--")

    def cancel_timer(self):
        self.is_running = False
        self.timer.stop()
        self.progress.setValue(0)
        self.update_remaining_time_label()
        self.update_end_time_label()
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.cancel_flash()

    def reset_timer(self):
        self.cancel_timer()
        self.remaining_time = 0
        self.end_time = None
        self.progress.setValue(0)
        self.update_remaining_time_label()
        self.update_end_time_label()

    def remove_timer(self):
        self.cancel_timer()
        self.remove_callback(self)

    def time_up(self):
        if not self.is_running:
            return

        self.is_running = False
        self.timer.stop()  # 确保计时器停止，避免重复调用
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if self.notify_var:
            notification.notify(
                title="時間到！",
                message=f"計時器 {self.timer_id} - 備註: {self.note_entry.text()}",
                timeout=10
            )

        if self.sound_var:
            self.play_sound()

        self.flash_progress()

    def play_sound(self):
        if platform.system() == "Windows":
            winsound.Beep(1000, 500)

    def flash_progress(self):
        if self.flashing:
            return
        self.flashing = True
        self._flash_progress(True)

    def _flash_progress(self, toggle_on):
        if self.flashing:
            self.progress.setValue(self.progress.maximum() if toggle_on else 0)
        QtCore.QTimer.singleShot(250, lambda: self._flash_progress(not toggle_on) if self.flashing else None)

    def cancel_flash(self):
        self.flashing = False
        self.progress.setValue(0)


class CountdownApp(QtWidgets.QWidget):
    # 初始化主窗口
    def __init__(self):
        super().__init__()  # 初始化父類
        self.setWindowTitle("GleamTimerV7-By PCKuo")  # 設置窗口標題
        self.timer_count = 0  # 初始化計時器數量
        self.frames = []  # 初始化框架列表
        self.sound_var = True  # 初始化 sound_var (是否啟用音效)
        self.notify_var = True  # 初始化 notify_var (是否啟用通知)

        self.init_ui()  # 初始化 UI
        self.update_geometry()  # 更新窗口大小

    # 初始化 UI
    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)  # 創建主布局

        # 創建菜單欄
        self.menu_bar = QtWidgets.QMenuBar(self)

        # 添加“選項”菜單
        options_menu = self.menu_bar.addMenu("選項")

        # 添加“置頂”選項
        self.topmost_action = QtWidgets.QAction("置頂", self, checkable=True)
        self.topmost_action.triggered.connect(self.set_topmost)
        options_menu.addAction(self.topmost_action)

        # 添加“音效”選項
        self.sound_action = QtWidgets.QAction("音效", self, checkable=True)
        self.sound_action.setChecked(self.sound_var)
        self.sound_action.triggered.connect(self.toggle_sound)
        options_menu.addAction(self.sound_action)

        # 添加“通知”選項
        self.notify_action = QtWidgets.QAction("通知", self, checkable=True)
        self.notify_action.setChecked(self.notify_var)
        self.notify_action.triggered.connect(self.toggle_notify)
        options_menu.addAction(self.notify_action)

        # 添加“新增計時器”按鈕
        self.add_timer_action = QtWidgets.QAction("新增計時器", self)
        self.add_timer_action.triggered.connect(self.add_timers)
        self.menu_bar.addAction(self.add_timer_action)

        # 添加菜單欄到主布局
        main_layout.setMenuBar(self.menu_bar)

        # 添加計時器布局
        self.timer_layout = QtWidgets.QGridLayout()  # QGridLayout（網格佈局）
        self.timer_layout.setSpacing(5)  # 設置網格間距
        main_layout.addLayout(self.timer_layout)  # 將計時器布局添加到主布局

        # 添加記事欄
        self.multiline_input = QtWidgets.QTextEdit()
        self.multiline_input.setPlaceholderText("記事欄")  # 設置佔位符文本
        # 設置 QTextEdit 的最小和最大高度為三行文本的高度
        font_metrics = self.multiline_input.fontMetrics()  # 獲取字體度量(字元寬度、高度、基線位)
        line_height = font_metrics.lineSpacing()  # 獲取行高
        self.multiline_input.setFixedHeight(line_height * 3 + 10)  # 設置 QTextEdit 的高度
        self.multiline_input.textChanged.connect(self.on_text_changed)  # 連接文本變化信號
        main_layout.addWidget(self.multiline_input)  # 將 QTextEdit 添加到主布局
        self.setLayout(main_layout)  # 設置主布局

        # 初始化顯示三個計時器
        self.add_timers()

    # 文本變化時的處理函數
    def on_text_changed(self):
        text = self.multiline_input.toPlainText()
        if "李宜儒" in text and "是新莊最漂亮的" not in text:
            self.multiline_input.blockSignals(True)  # 阻止信號以避免遞歸調用
            self.multiline_input.setPlainText(text + "是新莊最漂亮的")
            self.multiline_input.blockSignals(False)
            # 移動光標到文本結尾
            cursor = self.multiline_input.textCursor()  # 取得 QTextEdit 的文本光標
            cursor.movePosition(QtGui.QTextCursor.End)  # 使用 QtGui.QTextCursor
            self.multiline_input.setTextCursor(cursor)  # 將光標移動到文本結尾

    # 置頂功能
    def set_topmost(self):
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.topmost_action.isChecked())  # 設置置頂
        self.show()  

    # 音效功能
    def toggle_sound(self):
        self.sound_var = self.sound_action.isChecked()

    # 通知功能
    def toggle_notify(self):
        self.notify_var = self.notify_action.isChecked()

    # 添加計時器
    def add_timers(self):
        for _ in range(3):
            self.timer_count += 1
            timer_frame = TimerWidget(self.timer_count, self.remove_timer, self.sound_var, self.notify_var)
            self.frames.append(timer_frame)

            # 計算行和列的位置
            row = (self.timer_count - 1) % 3  
            column = (self.timer_count - 1) // 3
            self.timer_layout.addWidget(timer_frame, row, column)

        self.update_geometry()

    # 移除計時器
    def remove_timer(self, timer_frame):
        index = self.frames.index(timer_frame)
        self.frames.remove(timer_frame)
        timer_frame.deleteLater()
        self.reposition_timers()
        self.update_geometry()

    # 重新排列計時器
    def reposition_timers(self):
        for index, frame in enumerate(self.frames):
            row = index % 3
            column = index // 3
            self.timer_layout.addWidget(frame, row, column)

    # 更新窗口大小
    def update_geometry(self):
        num_columns = (len(self.frames) - 1) // 3 + 1
        self.setFixedSize(360 * num_columns, 640)

# 主函數
def main():
    try:
        app = QtWidgets.QApplication(sys.argv)
        countdown_app = CountdownApp()
        countdown_app.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
