import sqlite3
from datetime import datetime

DB_NAME = "electricity_billing.db"

def connect():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = connect()
    cursor = conn.cursor()
    
    # ตารางผู้ใช้งาน
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        role TEXT,
                        user_type TEXT,
                        first_bill_month TEXT,
                        first_bill_year TEXT,
                        created_at TEXT)''')
                        
    # ตารางบิลค่าไฟ
    cursor.execute('''CREATE TABLE IF NOT EXISTS bills (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        b_month TEXT,
                        b_year TEXT,
                        meter_read INTEGER,
                        units INTEGER,
                        total_amount REAL,
                        admin_comment TEXT,
                        user_comment TEXT,
                        is_edited INTEGER DEFAULT 0,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
                        
    # ตาราง Log
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT,
                        target_user TEXT,
                        b_cycle TEXT,
                        timestamp TEXT)''')
                        
    # สร้าง Admin เริ่มต้น
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                       ('admin', 'admin123', 'admin', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()

def add_log(action, target_user="-", b_cycle="-"):
    conn = connect()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO logs (action, target_user, b_cycle, timestamp) VALUES (?, ?, ?, ?)",
                   (action, target_user, b_cycle, timestamp))
    conn.commit()
    conn.close()

def register_user(username, password, user_type):
    try:
        conn = connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO users (username, password, role, user_type, created_at) VALUES (?, ?, ?, ?, ?)",
                       (username, password, 'user', user_type, created_at))
        conn.commit()
        conn.close()
        add_log("Register Account", username)
        return True
    except sqlite3.IntegrityError:
        return False

def check_login(username, password):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, user_type FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, user_type, first_bill_month, first_bill_year FROM users WHERE role='user'")
    users = cursor.fetchall()
    conn.close()
    return users

def get_bill(user_id, month, year):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE user_id=? AND b_month=? AND b_year=?", (user_id, month, year))
    bill = cursor.fetchone()
    conn.close()
    return bill

def save_bill(user_id, month, year, meter_read, units, total_amount, is_edit=False, admin_comment=""):
    # 1. เช็คก่อนว่ามีบิลอยู่แล้วไหม (get_bill มันเปิด-ปิด Connection ของตัวเองไปแล้ว ปลอดภัย)
    existing = get_bill(user_id, month, str(year))
    
    # 2. เปิด Connection หลักสำหรับบันทึกบิล
    conn = connect()
    cursor = conn.cursor()
    username = cursor.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()[0]
    
    action_msg = "" # เตรียมตัวแปรเก็บข้อความ Log
    
    if existing:
        cursor.execute('''UPDATE bills SET meter_read=?, units=?, total_amount=?, admin_comment=?, is_edited=1 
                          WHERE id=?''', (meter_read, units, total_amount, admin_comment, existing[0]))
        action_msg = "Edit Bill"
    else:
        cursor.execute('''INSERT INTO bills (user_id, b_month, b_year, meter_read, units, total_amount, admin_comment) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', (user_id, month, str(year), meter_read, units, total_amount, admin_comment))
        action_msg = "Create Bill"
        
    # 3. บันทึกและปิด Connection หลักให้เรียบร้อยก่อน
    conn.commit()
    conn.close()
    
    # 4. ค่อยเรียกใช้ add_log ตอนที่ Database ว่างแล้ว (ไม่ Lock แล้ว)
    add_log(action_msg, username, f"{month} {year}")

def get_user_bills(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT b_month, b_year, meter_read, units, total_amount, is_edited, admin_comment, user_comment FROM bills WHERE user_id=? ORDER BY b_year DESC, b_month DESC", (user_id,))
    bills = cursor.fetchall()
    conn.close()
    return bills

def get_all_logs():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, action, target_user, b_cycle FROM logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return logs

def update_first_bill(user_id, month, year):
    conn = connect()
    cursor = conn.cursor()
    # ดึงชื่อ User มาเพื่อใช้บันทึกลง Log
    username = cursor.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()[0]
    
    # อัปเดตรอบบิลแรกของ User
    cursor.execute("UPDATE users SET first_bill_month=?, first_bill_year=? WHERE id=?", (month, year, user_id))
    
    conn.commit()
    conn.close()
    
    # บันทึกประวัติลง Log
    add_log("Set First Bill", username, f"{month} {year}")

def update_user_comment(user_id, month, year, comment):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bills 
        SET user_comment = ? 
        WHERE user_id = ? AND b_month = ? AND b_year = ?
    """, (comment, user_id, month, str(year)))
    conn.commit()
    conn.close()