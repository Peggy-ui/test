
import bcrypt
import pyinputplus as pyip

def generate_password_hash(password: str) -> str:
    """
    接收一個明文字符串密碼，返回其 bcrypt hash 值。
    """
    # 將明文密碼轉換成 bytes
    password_bytes = password.encode('utf-8')

    # 生成鹽 (salt)，使用 bcrypt 的預設計算強度
    salt = bcrypt.gensalt()

    # 生成密碼的哈希值
    password_hash = bcrypt.hashpw(password_bytes, salt)

    # 將 bytes 類型的哈希值轉換為 UTF-8 字符串並返回
    return password_hash.decode('utf-8')

if __name__ == "__main__":
    try:
        # 提示用戶輸入密碼，並以 '*' 遮蔽
        passwd = pyip.inputPassword("請輸入要生成 hash 的密碼:", mask='*')
        
        # 使用函數生成密碼的哈希
        hashed_password = generate_password_hash(passwd)
        
        print("\n" + "="*40)
        print("生成的密碼 Hash 值:")
        print(hashed_password)
        print("="*40)

    except Exception as e:
        print(f"發生錯誤: {e}")