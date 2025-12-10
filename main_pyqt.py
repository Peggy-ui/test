import os
import subprocess
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import (
    QApplication, QTextEdit, QMainWindow, QAction, QMessageBox,
    QComboBox, QInputDialog, QDialog, QVBoxLayout, QListWidget, QListWidgetItem
)

# --- 全域常數 ---
PAGE_NAMES = [f'page{i+1}' for i in range(20)]
CURRENT_DIR = os.getcwd()

COMMON_STYLESHEET = """
QMessageBox {
    background-color: #2b2b2b;
    color: white;
}
QDialog {
    background-color: #2b2b2b;
}
QLabel {
    color: white;
    text-align: center;
}
QPushButton {
    background-color: #3d3d3d;
    color: white;
    border-style: none;
    padding: 5px;
    min-height: 20px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #5d5d5d;
}
QPushButton:pressed {
    background-color: #484848;
}
QToolBar QToolButton {
    color: white;
}
QInputDialog {
    background-color: #2b2b2b;
    color: white;
}
QLineEdit {
    color: black; 
    background-color: white;
}
"""

class MainWindow(QMainWindow):
    """主應用程式視窗。"""
    def __init__(self, encryption_key):
        super(MainWindow, self).__init__()

        # --- 實例屬性 ---
        self.encryption_key = encryption_key
        self.page_index = 1
        self.saved_text = ""
        self.is_saving = False
        self.is_pinned = False
        self.git_check_completed = False
        
        # --- V8.2 搜尋屬性 ---
        self.last_search_term = ""

        # --- V8.1 字體設定 ---
        self.font_sizes = [16, 20, 24, 28, 32, 36]
        self.font_size_index = 0
        self.font_size = self.font_sizes[self.font_size_index]

        # --- 根據作業系統決定是否隱藏 subprocess 視窗 ---
        self.creation_flags = 0
        if os.name == 'nt':
            self.creation_flags = subprocess.CREATE_NO_WINDOW

        self.init_ui()
        self.check_and_create_files()
        self.load_saved_text()

        # 啟動時檢查一次 Git
        QtCore.QTimer.singleShot(0, self.check_git_config_and_update)

        # 每10分鐘檢查 Git 狀態的計時器
        self.git_check_timer = QtCore.QTimer(self)
        self.git_check_timer.timeout.connect(self.periodic_git_check)
        self.git_check_timer.start(600000)

    def check_and_create_files(self):
        """檢查所有分頁的存檔是否存在，若否則創建一個空的加密檔案。"""
        for page in PAGE_NAMES:
            file_path = f"{page}_auto_save.txt"
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    encrypted_data = self.encryption_key.encrypt("".encode('utf-8')).decode('utf-8')
                    f.write(encrypted_data)

    def init_ui(self):
        """初始化使用者介面。"""
        self.setWindowTitle("記事本 V8.5      Power by STK-PEGGY")
        self.setGeometry(100, 100, 600, 650)
        self.setStyleSheet("background-color: #2b2b2b;")
        self.text_edit = QTextEdit(self)
        self.text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setStyleSheet(f"background-color: #3d3d3d; color: white; font-size: {self.font_size}px;")
        self.setCentralWidget(self.text_edit)

        self.statusBar().setStyleSheet("background-color: #2b2b2b; color: white;")

        self.message_toolbar = QtWidgets.QToolBar(self)
        self.addToolBarBreak()
        self.addToolBar(QtCore.Qt.BottomToolBarArea, self.message_toolbar)

        self.message_label = QtWidgets.QLabel(self)
        self.message_label.setStyleSheet("color: white; font-size: 20px;")
        self.message_label.setText("")
        self.message_label.setAlignment(QtCore.Qt.AlignLeft)
        self.message_toolbar.addWidget(self.message_label)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.message_toolbar.addWidget(spacer)

        self.git_status_label = QtWidgets.QLabel("Git: 初始化中...", self)
        self.git_status_label.setStyleSheet("color: white;")
        self.message_toolbar.addWidget(self.git_status_label)

        toolbar = self.addToolBar('Tools')
        toolbar.setStyleSheet(COMMON_STYLESHEET)

        # --- V8.5 Emoji Update ---
        save_action = QAction('💾', self)
        save_action.setShortcut('Ctrl+S')
        save_action.setToolTip("存檔 (Ctrl+S)")
        save_action.triggered.connect(self.save_text)
        toolbar.addAction(save_action)

        pin_action = QAction('📍', self)
        pin_action.setToolTip("釘選/取消釘選")
        pin_action.triggered.connect(self.toggle_pinned)
        toolbar.addAction(pin_action)

        switch_font_size_action = QAction('🔠', self)
        switch_font_size_action.setToolTip("切換字體大小")
        switch_font_size_action.triggered.connect(self.switch_font_size)
        toolbar.addAction(switch_font_size_action)
        
        # --- V8.5 搜尋邏輯整合 ---
        search_action = QAction('🔍', self)
        search_action.setShortcut('Ctrl+F')
        search_action.setToolTip("搜尋 / 找下一個 (Ctrl+F)")
        search_action.triggered.connect(self.search_current_page)
        toolbar.addAction(search_action)

        search_all_action = QAction('🌐', self)
        search_all_action.setShortcut('Ctrl+Shift+F')
        search_all_action.setToolTip("搜尋全部 (Ctrl+Shift+F)")
        search_all_action.triggered.connect(self.search_all_pages)
        toolbar.addAction(search_all_action)
        # --- V8.5 結束 ---

        self.page_selector = QComboBox(self)
        self.page_selector.setMinimumWidth(200)
        self.page_selector.addItems([f'page{i+1}' for i in range(20)])
        self.page_selector.setStyleSheet("background-color: white; color: black;")
        self.page_selector.currentIndexChanged.connect(self.switch_page)
        self.page_selector.setFocusPolicy(QtCore.Qt.NoFocus) # NoFocus 避免 Enter 鍵觸發下拉選單
        toolbar.addWidget(self.page_selector)
        self.update_page_selector_titles()

        # --- V8.5 Emoji Update for Git ---
        upload_action = QAction('📤', self)
        upload_action.setToolTip("上傳 (Git Push)")
        upload_action.triggered.connect(lambda: self.git('upload'))
        toolbar.addAction(upload_action)

        download_action = QAction('📥', self)
        download_action.setToolTip("下載 (Git Pull)")
        download_action.triggered.connect(lambda: self.git('download'))
        toolbar.addAction(download_action)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.auto_save)
        self.timer.start(10000)

    def periodic_git_check(self):
        """每10分鐘執行一次的背景 Git 檢查。"""
        self.message_label_update("正在背景檢查遠端儲存庫...")
        git_config_path = os.path.join(CURRENT_DIR, '.git', 'config')
        if not os.path.exists(git_config_path):
            self.git_status_label.setText("Git 未使用")
            self.git_status_label.setStyleSheet("color: #888888;")
            return

        try:
            os.chdir(CURRENT_DIR)
            subprocess.run(["git", "fetch"], check=True, capture_output=True, creationflags=self.creation_flags)

            local_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], creationflags=self.creation_flags).decode('utf-8').strip()
            remote_commit = subprocess.check_output(["git", "rev-parse", "origin/master"], creationflags=self.creation_flags).decode('utf-8').strip()
            base_commit = subprocess.check_output(["git", "merge-base", "HEAD", "origin/master"], creationflags=self.creation_flags).decode('utf-8').strip()

            if local_commit == remote_commit:
                self.git_status_label.setText("✓ 已同步")
                self.git_status_label.setStyleSheet("color: #7CFC00;")
            elif base_commit == local_commit:
                self.git_status_label.setText("🔄 遠端有新版本！")
                self.git_status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            elif base_commit == remote_commit:
                self.git_status_label.setText("↑ 本地待上傳")
                self.git_status_label.setStyleSheet("color: #FFFF00;")
            else:
                self.git_status_label.setText("↔️ 分支已分歧")
                self.git_status_label.setStyleSheet("color: #FF4500;")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.git_status_label.setText("Git 檢查錯誤")
            self.git_status_label.setStyleSheet("color: red;")

    def check_git_config_and_update(self):
        """啟動時檢查 Git 設定並決定是否提示更新。"""
        self.message_label_update("正在檢查 Git 配置...")
        git_config_path = os.path.join(CURRENT_DIR, '.git', 'config')

        if not os.path.exists(git_config_path):
            self.git_status_label.setText("Git 未使用")
            self.git_status_label.setStyleSheet("color: #888888;")
            self.git_check_completed = True
            return

        if self.check_git():
            try:
                os.chdir(CURRENT_DIR)
                subprocess.run(["git", "fetch"], check=True, capture_output=True, creationflags=self.creation_flags)

                local = subprocess.check_output(["git", "rev-parse", "HEAD"], creationflags=self.creation_flags).decode('utf-8').strip()
                remote = subprocess.check_output(["git", "rev-parse", "origin/master"], creationflags=self.creation_flags).decode('utf-8').strip()
                base = subprocess.check_output(["git", "merge-base", "HEAD", "origin/master"], creationflags=self.creation_flags).decode('utf-8').strip()

                if local == remote:
                    self.git_status_label.setText("✓ 已同步")
                    self.git_status_label.setStyleSheet("color: #7CFC00;")
                elif base == local:
                    self.git_status_label.setText("🔄 遠端有新版本！")
                    self.git_status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
                    self.prompt_git_pull()
                elif base == remote:
                    self.git_status_label.setText("↑ 本地待上傳")
                    self.git_status_label.setStyleSheet("color: #FFFF00;")
                else:
                    self.git_status_label.setText("↔️ 分支已分歧")
                    self.git_status_label.setStyleSheet("color: #FF4500;")

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.handle_error(e)
                self.git_status_label.setText("Git 檢查錯誤")
                self.git_status_label.setStyleSheet("color: red;")

        self.git_check_completed = True

    def prompt_git_pull(self):
        """當遠端有更新時，跳出視窗詢問使用者是否要拉取。"""
        choice = QMessageBox()
        choice.setWindowTitle("更新")
        choice.setText("本地分支落後於遠程分支，是否要拉取更新?")
        choice.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        choice.setIcon(QMessageBox.Question)
        choice.setStyleSheet(COMMON_STYLESHEET)
        result = choice.exec_()
        if result == QMessageBox.Yes:
            try:
                subprocess.run(["git", "pull"], check=True, capture_output=True, creationflags=self.creation_flags)
                self.message_label_update("已成功拉取最新的遠程分支。")
                self.git_status_label.setText("✓ 已同步")
                self.git_status_label.setStyleSheet("color: #7CFC00;")
                self.switch_page(0)
            except (subprocess.CalledProcessError, Exception) as e:
                self.handle_error(e)

    def update_page_selector_titles(self):
        """更新下拉選單中所有分頁的標題，以其內容的第一行為準。"""
        for i, page in enumerate(PAGE_NAMES):
            try:
                with open(f"{page}_auto_save.txt", "r", encoding="utf-8") as f:
                    encrypted_data = f.read().encode('utf-8')
                    title_to_set = f"{i+1}. "
                    if encrypted_data:
                        try:
                            decrypted_data = self.encryption_key.decrypt(encrypted_data).decode('utf-8')
                            first_line = decrypted_data.split('\n', 1)[0].strip()
                            if first_line:
                                title_to_set = f"{i+1}.{first_line}"
                        except InvalidToken:
                            pass
                    self.page_selector.setItemText(i, title_to_set)
            except FileNotFoundError:
                self.page_selector.setItemText(i, f"{i+1}. ")
            except Exception as e:
                self.handle_error(e)

    def message_label_update(self, text):
        """更新底部狀態欄的訊息，並在2秒後自動清除。"""
        self.message_label.setText(text)
        timer = QtCore.QTimer(self)
        timer.singleShot(2000, self.clear_message)

    def clear_message(self):
        """清除底部狀態欄的訊息。"""
        try:
            self.message_label.setText("")
        except RuntimeError: # 視窗可能已關閉
            pass

    def handle_error(self, e):
        """統一的錯誤處理，以訊息框顯示錯誤。"""
        msg_box = QMessageBox()
        msg_box.setText("錯誤!")
        msg_box.setInformativeText(str(e))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStyleSheet(COMMON_STYLESHEET)
        msg_box.exec_()

    def save_text(self):
        """將當前編輯器中的文字加密並儲存至檔案。"""
        if not self.git_check_completed or self.is_saving:
            return
        try:
            text_str = self.text_edit.toPlainText().rstrip()
            if text_str != self.saved_text:
                self.is_saving = True
                encrypted_data = self.encryption_key.encrypt(text_str.encode('utf-8')).decode('utf-8')
                with open(f"{PAGE_NAMES[self.page_index - 1]}_auto_save.txt", "w", encoding="utf-8") as f:
                    f.write(encrypted_data)
                self.saved_text = text_str

                first_line = text_str.split('\n', 1)[0].strip()
                title_to_set = f"{self.page_index}.{first_line}" if first_line else f"{self.page_index}. "
                self.page_selector.setItemText(self.page_index - 1, title_to_set)

                self.is_saving = False
        except Exception as e:
            self.is_saving = False
            self.handle_error(e)

    def switch_page(self, index):
        """切換分頁。"""
        if index == -1:
            return

        self.save_text()
        self.page_index = index + 1
        try:
            self.message_label_update(f"切換分頁:{self.page_index}")
            with open(f"{PAGE_NAMES[self.page_index - 1]}_auto_save.txt", "r", encoding="utf-8") as f:
                encrypted_data = f.read().encode('utf-8')
                if encrypted_data:
                    try:
                        decrypted_data = self.encryption_key.decrypt(encrypted_data).decode('utf-8')
                        self.saved_text = decrypted_data
                        self.text_edit.clear()
                        self.text_edit.insertPlainText(self.saved_text)
                    except InvalidToken:
                        self.handle_error("無效的密碼或加密數據。")
                        self.saved_text = ""
                        self.text_edit.clear()
                else:
                    self.saved_text = ""
                    self.text_edit.clear()
        except FileNotFoundError:
            self.create_empty_file(self.page_index - 1)
        except Exception as e:
            self.handle_error(e)

        self.update_page_selector_titles()
        self.page_selector.setCurrentIndex(self.page_index - 1)

    def create_empty_file(self, page_index):
        """創建一個新的空檔案。"""
        with open(f"{PAGE_NAMES[page_index]}_auto_save.txt", "w", encoding="utf-8") as f:
            encrypted_data = self.encryption_key.encrypt("".encode('utf-8')).decode('utf-8')
            f.write(encrypted_data)
        self.saved_text = ""
        self.text_edit.clear()

    def auto_save(self):
        """自動儲存功能。"""
        try:
            text_str = self.text_edit.toPlainText().rstrip()
            if text_str != self.saved_text:
                if self.git_check_completed:
                    self.save_text()
                    self.message_label_update("自動儲存...")
                else:
                    self.message_label_update("Git未結束,略過儲存")
            self.timer.start(10000)
        except Exception as e:
            self.handle_error(e)

    def toggle_pinned(self):
        """切換視窗置頂狀態。"""
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.message_label_update("已釘選")
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.message_label_update("取消釘選")
        self.show()

    def switch_font_size(self):
        """循環切換字體大小。"""
        self.font_size_index = (self.font_size_index + 1) % len(self.font_sizes)
        self.font_size = self.font_sizes[self.font_size_index]
        self.message_label_update(f"文字縮放: {self.font_size}px")
        self.text_edit.setStyleSheet(f"background-color: #3d3d3d; color: white; font-size: {self.font_size}px;")
        self.message_label.setStyleSheet(f"color: white; font-size: {self.font_size-4}px;")

    def load_saved_text(self):
        """從檔案載入加密的文字並解密顯示。"""
        try:
            with open(f"{PAGE_NAMES[self.page_index - 1]}_auto_save.txt", "r", encoding="utf-8") as f:
                encrypted_data = f.read().encode('utf-8')
                if encrypted_data:
                    try:
                        decrypted_data = self.encryption_key.decrypt(encrypted_data).decode('utf-8')
                        self.saved_text = decrypted_data
                        self.text_edit.clear()
                        self.text_edit.insertPlainText(self.saved_text)
                    except InvalidToken:
                        self.handle_error("無效的密碼或加密數據。")
                        return
        except FileNotFoundError:
            self.create_empty_file(self.page_index - 1)
        except Exception as e:
            self.handle_error(e)

    # --- V8.5 優化: 搜尋功能 (整合找下一個) ---
    def search_current_page(self):
        """搜尋目前分頁。"""
        
        # 使用 QInputDialog，父視窗設為 None 避免繼承樣式
        dialog = QInputDialog(None) 
        dialog.setWindowTitle('搜尋')
        dialog.setLabelText('請輸入要搜尋的文字:')
        dialog.setTextValue(self.last_search_term) # 預設帶入上次的搜尋字
        
        # 顯示對話框
        ok = dialog.exec_()
        text = dialog.textValue()

        if ok and text:
            # 邏輯判斷: 若輸入新字，重頭開始；若輸入舊字，繼續往下找
            if text != self.last_search_term:
                self.last_search_term = text
                self.text_edit.moveCursor(QtGui.QTextCursor.Start)
            
            # 開始搜尋 (若未重置游標，則從當前位置往下找 = Find Next)
            found = self.text_edit.find(text)

            if not found:
                # 處理找不到的情況 (可能是到底了)
                choice = QMessageBox.question(None, '搜尋',
                                            f"已搜尋至文件結尾或找不到 '{text}'。\n是否要從頭開始搜尋？",
                                            QMessageBox.Yes | QMessageBox.No)
                
                if choice == QMessageBox.Yes:
                    self.text_edit.moveCursor(QtGui.QTextCursor.Start)
                    found_retry = self.text_edit.find(text)
                    if not found_retry:
                        QMessageBox.information(None, "搜尋結果", f"在目前分頁中找不到 '{text}'")

    def search_all_pages(self):
        """搜尋所有分頁。"""
        
        dialog = QInputDialog(None) 
        dialog.setWindowTitle('搜尋全部')
        dialog.setLabelText('請輸入要搜尋的文字:')

        ok = dialog.exec_()
        search_term = dialog.textValue()

        if not (ok and search_term):
            return

        self.message_label_update(f"正在搜尋 '{search_term}'...")
        QApplication.processEvents() 

        found_pages = []
        for i, page in enumerate(PAGE_NAMES):
            try:
                file_path = f"{page}_auto_save.txt"
                if not os.path.exists(file_path):
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    encrypted_data = f.read().encode('utf-8')
                
                if not encrypted_data:
                    continue
                
                decrypted_data = self.encryption_key.decrypt(encrypted_data).decode('utf-8')
                
                if search_term.lower() in decrypted_data.lower():
                    first_line = decrypted_data.split('\n', 1)[0].strip()
                    if not first_line:
                        first_line = f"Page {i+1} (無標題)"
                    found_pages.append((i, first_line)) 

            except (InvalidToken, FileNotFoundError):
                continue 
            except Exception as e:
                self.handle_error(f"搜尋 {page} 時發生錯誤: {e}")
        
        self.clear_message() 
        self.last_search_term = search_term 

        # --- 顯示結果 ---
        if not found_pages:
            QMessageBox.information(None, "搜尋結果", f"在所有分頁中都找不到 '{search_term}'。")
            return

        # 創建一個新的對話框來顯示結果
        results_dialog = QDialog(self)
        results_dialog.setWindowTitle("搜尋結果")
        results_dialog.setStyleSheet(COMMON_STYLESHEET)
        results_dialog.setMinimumWidth(400)
        layout = QVBoxLayout()
        
        label = QtWidgets.QLabel(f"找到 '{search_term}' 於 {len(found_pages)} 個分頁中：")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet("background-color: #3d3d3d; color: white; font-size: 16px;")
        
        for i, title in found_pages:
            item_text = f"{i+1}. {title}"
            item = QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, i) 
            list_widget.addItem(item)
        
        list_widget.itemDoubleClicked.connect(self.go_to_search_result)
        list_widget.itemDoubleClicked.connect(results_dialog.accept) 
        
        layout.addWidget(list_widget)
        results_dialog.setLayout(layout)
        results_dialog.exec_()

    def go_to_search_result(self, item):
        """從全域搜尋結果點擊後跳轉分頁並高亮。"""
        page_index = item.data(QtCore.Qt.UserRole)
        
        self.page_selector.setCurrentIndex(page_index)
        
        self.text_edit.moveCursor(QtGui.QTextCursor.Start)
        found = self.text_edit.find(self.last_search_term)
        if not found:
            self.text_edit.moveCursor(QtGui.QTextCursor.Start)

    def check_git(self):
        """檢查系統是否安裝了 Git。"""
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True, creationflags=self.creation_flags)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.handle_error(e)
            return False

    def git(self, action):
        """處理 Git 的上傳與下載操作。"""
        if not self.check_git():
            QMessageBox.critical(self, "錯誤!", "未安裝Git!")
            return
        try:
            msg_box = QMessageBox()
            msg_box.setText(f"是否要進行 {action}?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setStyleSheet(COMMON_STYLESHEET)
            choice = msg_box.exec()
            if choice == QMessageBox.Yes:
                if action == "upload":
                    self.git_upload()
                elif action == "download":
                    self.git_download()
                self.periodic_git_check()
            else:
                self.message_label_update(f"{action}已取消")
        except (subprocess.CalledProcessError, Exception) as e:
            self.handle_error(e)
            self.message_label_update(f"{action}失敗!")
            self.periodic_git_check()

    def git_upload(self):
        """執行 Git 上傳。"""
        self.save_text()
        self.message_label_update("上傳中...")
        os.chdir(CURRENT_DIR)
        output = subprocess.check_output(["git", "status", "--porcelain"], creationflags=self.creation_flags)
        if not output.strip():
            self.message_label_update("無需上傳，已是最新狀態！")
            return
        subprocess.run(["git", "add", "."], check=True, creationflags=self.creation_flags)
        subprocess.run(["git", "commit", "-m", "upload by 記事本"], check=True, creationflags=self.creation_flags)
        subprocess.run(["git", "push", "-u", "origin", "master"], check=True, creationflags=self.creation_flags)
        self.message_label_update("上傳成功!")

    def git_download(self):
        """執行 Git 下載。"""
        self.message_label_update("下載中...")
        os.chdir(CURRENT_DIR)
        subprocess.run(["git", "fetch", "--all"], check=True, creationflags=self.creation_flags)
        subprocess.run(["git", "reset", "--hard", "origin/master"], check=True, creationflags=self.creation_flags)
        self.switch_page(0)
        self.message_label_update("下載成功!")

def prompt_password():
    """提示使用者輸入密碼，並驗證其正確性。"""
    while True:
        password, ok = QInputDialog.getText(None, '密碼', '請輸入密碼:', QtWidgets.QLineEdit.Password)
        if not ok:
            return None

        if password:
            key = hashlib.sha256(password.encode()).digest()
            encryption_key = Fernet(base64.urlsafe_b64encode(key))

            try:
                first_page_path = f"{PAGE_NAMES[0]}_auto_save.txt"
                if not os.path.exists(first_page_path):
                    with open(first_page_path, "w", encoding="utf-8") as f:
                        f.write(encryption_key.encrypt("".encode('utf-8')).decode('utf-8'))

                with open(first_page_path, "r", encoding="utf-8") as f:
                    encrypted_data = f.read().encode('utf-8')
                    encryption_key.decrypt(encrypted_data)
                return encryption_key
            except InvalidToken:
                QMessageBox.critical(None, "錯誤", "密碼無效，請重試。")
            except Exception as e:
                QMessageBox.critical(None, "錯誤", f"發生預期外的錯誤: {e}")
        else:
            QMessageBox.critical(None, "錯誤", "密碼不能為空，請重試。")

if __name__ == "__main__":
    app = QApplication([])

    main_encryption_key = prompt_password()

    if main_encryption_key:
        window = MainWindow(encryption_key=main_encryption_key)
        window.show()
        app.exec_()
    else:
        app.quit()