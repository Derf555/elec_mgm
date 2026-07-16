import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import database as db
from datetime import datetime
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- ฟังก์ชันคำนวณอัตราขั้นบันไดจำลอง ---
def calculate_bill(units, user_type):
    total = 0
    if user_type == "บ้านอยู่อาศัย":
        if units <= 15: total = units * 2.3
        elif units <= 25: total = (15 * 2.3) + ((units - 15) * 3.2)
        else: total = (15 * 2.3) + (10 * 3.2) + ((units - 25) * 4.2)
    else: # กิจการ
        total = units * 5.5
    return round(total, 2)

class BillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ระบบจัดการค่าไฟ (Mini Project)")
        self.root.geometry("950x650") # ขยายหน้าต่างขึ้นเล็กน้อยให้ดูสบายตาขึ้น
        db.init_db()
        self.current_user = None
        self.show_login()

    def clear_frame(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # ================= LOGIN & REGISTER =================
    def show_login(self):
        self.clear_frame()
        frame = tk.Frame(self.root, pady=50)
        frame.pack()
        
        tk.Label(frame, text="เข้าสู่ระบบ", font=("Arial", 20, "bold")).pack(pady=10)
        tk.Label(frame, text="Username").pack()
        self.entry_user = tk.Entry(frame)
        self.entry_user.pack(pady=5)
        tk.Label(frame, text="Password").pack()
        self.entry_pass = tk.Entry(frame, show="*")
        self.entry_pass.pack(pady=5)
        
        tk.Button(frame, text="Login", command=self.login, bg="lightblue").pack(pady=10)
        
        tk.Label(frame, text="--- หรือสร้างบัญชีสำหรับ User ---").pack(pady=10)
        self.user_type_var = tk.StringVar(value="บ้านอยู่อาศัย")
        ttk.Combobox(frame, textvariable=self.user_type_var, values=["บ้านอยู่อาศัย", "กิจการขนาดเล็ก"]).pack(pady=5)
        tk.Button(frame, text="Register User", command=self.register).pack()

    def register(self):
        u, p, t = self.entry_user.get(), self.entry_pass.get(), self.user_type_var.get()
        if u and p:
            if db.register_user(u, p, t):
                messagebox.showinfo("Success", "สมัครสมาชิกสำเร็จ!")
            else:
                messagebox.showerror("Error", "Username นี้มีอยู่แล้ว")
        else:
            messagebox.showwarning("Warning", "กรุณากรอกข้อมูลให้ครบ")

    def login(self):
        u, p = self.entry_user.get(), self.entry_pass.get()
        user_data = db.check_login(u, p)
        if user_data:
            self.current_user = user_data
            if user_data[2] == 'admin':
                self.show_admin_panel()
            else:
                self.show_user_panel()
        else:
            messagebox.showerror("Error", "รหัสผ่านไม่ถูกต้อง")

    def logout(self):
        self.current_user = None
        self.show_login()

    # ================= ADMIN PANEL =================
    def show_admin_panel(self):
        self.clear_frame()
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both')
        
        tab_input = tk.Frame(notebook)
        tab_settings = tk.Frame(notebook)
        tab_logs = tk.Frame(notebook)
        
        notebook.add(tab_input, text='Input บิลค่าไฟ')
        notebook.add(tab_settings, text='User Settings')
        notebook.add(tab_logs, text='Logs')
        
        tk.Button(self.root, text="Logout", command=self.logout, bg="red", fg="white").pack(pady=5)
        
        self.setup_admin_input(tab_input)
        self.setup_admin_settings(tab_settings)
        self.setup_admin_logs(tab_logs)

    def setup_admin_input(self, frame):
        top_f = tk.Frame(frame, pady=10)
        top_f.pack()
        tk.Label(top_f, text="รอบบิล ปี:").grid(row=0, column=0)
        self.cb_year = ttk.Combobox(top_f, values=[str(y) for y in range(2025, 2031)])
        self.cb_year.set(datetime.now().year)
        self.cb_year.grid(row=0, column=1, padx=5)
        
        tk.Label(top_f, text="เดือน:").grid(row=0, column=2)
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        self.cb_month = ttk.Combobox(top_f, values=months)
        self.cb_month.set(months[datetime.now().month - 1])
        self.cb_month.grid(row=0, column=3, padx=5)
        
        tk.Button(top_f, text="โหลดข้อมูลผู้ใช้", command=self.load_users_for_input).grid(row=0, column=4, padx=10)
        
        # ⚡ [เพิ่ม Scrollbar] สำหรับตาราง Input บิล
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tree_admin_input = ttk.Treeview(tree_frame, columns=("ID", "User", "Type", "Status"), show="headings")
        self.tree_admin_input.heading("ID", text="ID")
        self.tree_admin_input.heading("User", text="Username")
        self.tree_admin_input.heading("Type", text="ประเภท")
        self.tree_admin_input.heading("Status", text="สถานะเดือนนี้")
        
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_admin_input.yview)
        self.tree_admin_input.configure(yscrollcommand=scroll.set)
        
        self.tree_admin_input.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        # ส่วนกรอกข้อมูลด้านล่าง
        bot_f = tk.Frame(frame, pady=5)
        bot_f.pack()
        tk.Label(bot_f, text="เลขมิเตอร์ใหม่ (หน่วย):").grid(row=0, column=0)
        self.ent_meter = tk.Entry(bot_f)
        self.ent_meter.grid(row=0, column=1)
        
        tk.Label(bot_f, text="เหตุผล/Comment (กรณีแก้ไข):").grid(row=1, column=0)
        self.ent_comment = tk.Entry(bot_f)
        self.ent_comment.grid(row=1, column=1)
        
        tk.Button(bot_f, text="บันทึก / อัปเดตบิล", command=self.save_bill_admin).grid(row=2, columnspan=2, pady=5)

    def load_users_for_input(self):
        for row in self.tree_admin_input.get_children():
            self.tree_admin_input.delete(row)
            
        users = db.get_all_users()
        sel_m_str, sel_y_str = self.cb_month.get(), self.cb_year.get()
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        
        try:
            sel_y = int(sel_y_str)
            sel_m = months.index(sel_m_str) + 1 
        except ValueError:
            return

        for u in users:
            f_month_str, f_year_str = u[3], u[4]
            if not f_month_str or f_month_str == "-" or not f_year_str or f_year_str == "-":
                continue
                
            f_y = int(f_year_str)
            f_m = months.index(f_month_str) + 1
            
            if sel_y < f_y or (sel_y == f_y and sel_m < f_m):
                continue

            bill = db.get_bill(u[0], sel_m_str, sel_y_str)
            # แก้ไขตรงนี้เรียบร้อย เปลี่ยนจาก bill[4] เป็น bill[5] เพื่อดึงจำนวนหน่วยที่ใช้จริง
            status = f"จดแล้ว ({bill[5]} หน่วย)" if bill else "ยังไม่ได้จด"
            self.tree_admin_input.insert("", "end", values=(u[0], u[1], u[2], status))

    def save_bill_admin(self):
        selected = self.tree_admin_input.selection()
        if not selected:
            messagebox.showwarning("เตือน", "กรุณาคลิกเลือกผู้ใช้งานในตารางก่อน")
            return
        
        item = self.tree_admin_input.item(selected[0])['values']
        uid, uname, utype, status = item[0], item[1], item[2], item[3]
        m, y = self.cb_month.get(), self.cb_year.get()
        meter_val = str(self.ent_meter.get()).strip()
        comment = str(self.ent_comment.get()).strip()
        
        if not meter_val.isdigit():
            messagebox.showerror("Error", "เลขมิเตอร์ต้องเป็นตัวเลขเท่านั้น!")
            return
            
        current_meter = int(meter_val)
        
        # ดึงข้อมูลรอบบิลเริ่มต้นมาเช็คเงื่อนไข baseline
        users = db.get_all_users()
        user_info = next((u for u in users if u[0] == uid), None)
        f_month = user_info[3] if user_info else None
        f_year = user_info[4] if user_info else None
        
        # ถ้ารอบบิลตรงกับรอบเริ่มต้น ให้เก็บค่ามิเตอร์ฐานไว้ (หน่วยการใช้เป็น 0)
        if m == f_month and str(y) == str(f_year):
            units_used = 0
            total = 0.0
        else:
            months = ["January", "February", "March", "April", "May", "June", 
                      "July", "August", "September", "October", "November", "December"]
            current_idx = months.index(m)
            
            if current_idx == 0:
                prev_m = "December"
                prev_y = str(int(y) - 1)
            else:
                prev_m = months[current_idx - 1]
                prev_y = str(y)
                
            prev_bill = db.get_bill(uid, prev_m, prev_y)
            prev_meter = prev_bill[3] if prev_bill else 0 
            
            if current_meter < prev_meter:
                messagebox.showerror("Error", f"เลขมิเตอร์ใหม่ ({current_meter}) ต้องห้ามลบกระโดดถอยหลังกว่าครั้งก่อน ({prev_meter})!")
                return
                
            units_used = current_meter - prev_meter
            total = calculate_bill(units_used, utype)
            
        is_edit = "จดแล้ว" in status
        if is_edit and not comment:
            messagebox.showerror("Error", "กรณีแก้ไขข้อมูล บังคับให้ต้องใส่ Comment (เหตุผล) ทุกครั้ง!")
            return
            
        db.save_bill(uid, m, str(y), current_meter, units_used, total, is_edit, comment)
        
        self.ent_meter.delete(0, tk.END)
        self.ent_comment.delete(0, tk.END)
        messagebox.showinfo("Success", f"บันทึกค่าไฟ {uname} รอบ {m} {y} เรียบร้อยแล้ว\n(ใช้ไป {units_used} หน่วย | รวมเงิน {total:,.2f} บาท)")
        
        self.load_users_for_input()
        self.load_admin_logs()

    def setup_admin_settings(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()
            
        # ⚡ [เพิ่ม Scrollbar] สำหรับตารางตั้งค่ารอบบิลแรกของ User
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree_admin_settings = ttk.Treeview(tree_frame, columns=("ID", "User", "Type", "FirstBill"), show="headings")
        self.tree_admin_settings.heading("ID", text="ID")
        self.tree_admin_settings.heading("User", text="Username")
        self.tree_admin_settings.heading("Type", text="ประเภท")
        self.tree_admin_settings.heading("FirstBill", text="รอบบิลเริ่มต้น")
        
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_admin_settings.yview)
        self.tree_admin_settings.configure(yscrollcommand=scroll.set)
        
        self.tree_admin_settings.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        bot_f = tk.Frame(frame, pady=10)
        bot_f.pack()
        
        tk.Label(bot_f, text="ตั้งค่ารอบบิลแรก ปี:").grid(row=0, column=0, padx=5)
        self.cb_set_year = ttk.Combobox(bot_f, values=[str(y) for y in range(2025, 2031)])
        self.cb_set_year.set(datetime.now().year)
        self.cb_set_year.grid(row=0, column=1, padx=5)
        
        tk.Label(bot_f, text="เดือน:").grid(row=0, column=2, padx=5)
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        self.cb_set_month = ttk.Combobox(bot_f, values=months)
        self.cb_set_month.set(months[datetime.now().month - 1])
        self.cb_set_month.grid(row=0, column=3, padx=5)
        
        tk.Button(bot_f, text="บันทึกรอบบิลแรก", command=self.save_first_bill, bg="lightgreen").grid(row=0, column=4, padx=10)
        self.load_users_for_settings()

    def load_users_for_settings(self):
        for row in self.tree_admin_settings.get_children():
            self.tree_admin_settings.delete(row)
            
        users = db.get_all_users()
        for u in users:
            f_month = u[3] if u[3] else "-"
            f_year = u[4] if u[4] else "-"
            first_bill = f"{f_month} {f_year}" if f_month != "-" else "ยังไม่ได้ตั้งค่า"
            self.tree_admin_settings.insert("", "end", values=(u[0], u[1], u[2], first_bill))

    def save_first_bill(self):
        selected = self.tree_admin_settings.selection()
        if not selected:
            messagebox.showwarning("เตือน", "กรุณาคลิกเลือก User ในตารางที่ต้องการตั้งค่าก่อน!")
            return
        
        item = self.tree_admin_settings.item(selected[0])['values']
        uid, uname = item[0], item[1]
        m, y = self.cb_set_month.get(), self.cb_set_year.get()
        
        db.update_first_bill(uid, m, y)
        messagebox.showinfo("Success", f"ตั้งค่ารอบบิลแรกให้ '{uname}' เป็น {m} {y} เรียบร้อยแล้ว!")
        
        self.load_users_for_settings()
        self.load_admin_logs()

    def setup_admin_logs(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()
            
        # ⚡ [เพิ่ม Scrollbar] สำหรับตารางประวัติแอดมิน (Log)
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree_admin_logs = ttk.Treeview(tree_frame, columns=("Time", "Action", "User", "Cycle"), show="headings")
        self.tree_admin_logs.heading("Time", text="เวลา")
        self.tree_admin_logs.heading("Action", text="การกระทำ")
        self.tree_admin_logs.heading("User", text="ผู้ใช้เป้าหมาย")
        self.tree_admin_logs.heading("Cycle", text="รอบบิล")
        
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_admin_logs.yview)
        self.tree_admin_logs.configure(yscrollcommand=scroll.set)
        
        self.tree_admin_logs.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        self.load_admin_logs()

    def load_admin_logs(self):
        if hasattr(self, 'tree_admin_logs'):
            for row in self.tree_admin_logs.get_children():
                self.tree_admin_logs.delete(row)
            for log in db.get_all_logs():
                self.tree_admin_logs.insert("", "end", values=log)

    # ================= USER PANEL =================
    def show_user_panel(self):
        self.clear_frame()
        
        # Top: Dashboard
        dash_f = tk.Frame(self.root, bg="#f0f0f0", height=230)
        dash_f.pack(fill="x", padx=10, pady=5)
        
        bills = db.get_user_bills(self.current_user[0])
        total_bills = len(bills)
        avg_bill = sum(b[4] for b in bills) / total_bills if total_bills else 0
        max_bill = max([b[4] for b in bills]) if total_bills else 0
        
        tk.Label(dash_f, text=f"ยินดีต้อนรับ {self.current_user[1]}", font=("Arial", 16, "bold"), bg="#f0f0f0").pack()
        tk.Label(dash_f, text=f"บิลเฉลี่ยของคุณ: {avg_bill:,.2f} บาท | บิลสูงสุดตลอดกาล: {max_bill:,.2f} บาท", bg="#f0f0f0").pack()
        
        if total_bills > 0:
            fig, ax = plt.subplots(figsize=(5, 1.8))
            months = [f"{b[0][:3]} {b[1][-2:]}" for b in bills[:6][::-1]]
            amounts = [b[4] for b in bills[:6][::-1]]
            ax.plot(months, amounts, marker='o', color='orange')
            canvas = FigureCanvasTkAgg(fig, master=dash_f)
            canvas.get_tk_widget().pack()

        # Bottom: Bill List 
        list_f = tk.Frame(self.root)
        list_f.pack(fill="both", expand=True, padx=10, pady=5)
        
        # ⚡ [เพิ่ม Scrollbar] สำหรับตารางประวัติบิลฝั่ง User
        self.tree_user = ttk.Treeview(list_f, columns=("Cycle", "Meter", "Units", "Total", "AdminCmnt", "UserCmnt"), show="headings")
        self.tree_user.heading("Cycle", text="รอบบิล")
        self.tree_user.heading("Meter", text="เลขมิเตอร์")
        self.tree_user.heading("Units", text="หน่วยที่ใช้")
        self.tree_user.heading("Total", text="ยอดสุทธิ (บาท)")
        self.tree_user.heading("AdminCmnt", text="หมายเหตุแอดมิน")
        self.tree_user.heading("UserCmnt", text="หมายเหตุผู้ใช้")
        
        self.tree_user.tag_configure('edited', background='#ffcccb') 
        
        scroll = ttk.Scrollbar(list_f, orient="vertical", command=self.tree_user.yview)
        self.tree_user.configure(yscrollcommand=scroll.set)
        
        self.tree_user.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        for b in bills:
            cycle = f"{b[0]} {b[1]}"
            tags = ('edited',) if b[5] == 1 else ()
            self.tree_user.insert("", "end", values=(cycle, b[2], b[3], b[4], b[6], b[7]), tags=tags)
            
        btn_f = tk.Frame(self.root, pady=5)
        btn_f.pack()
        tk.Button(btn_f, text="พิมพ์บิล (Printout)", command=self.print_bill).grid(row=0, column=0, padx=5)
        tk.Button(btn_f, text="Export CSV", command=self.export_csv).grid(row=0, column=1, padx=5)
        tk.Button(btn_f, text="จำลองค่าไฟ", command=self.simulate_bill).grid(row=0, column=2, padx=5)
        tk.Button(btn_f, text="เพิ่มหมายเหตุ/แจ้งเรื่อง", command=self.add_user_comment, bg="lightyellow").grid(row=0, column=3, padx=5)
        tk.Button(btn_f, text="Logout", command=self.logout, bg="red", fg="white").grid(row=0, column=4, padx=5)

    def add_user_comment(self):
        selected = self.tree_user.selection()
        if not selected:
            messagebox.showwarning("เตือน", "กรุณาคลิกเลือกรอบบิลในตารางที่ต้องการเพิ่มหมายเหตุก่อน")
            return
            
        item = self.tree_user.item(selected[0])['values']
        cycle_str = item[0] 
        month, year = cycle_str.split() 
        
        comment = simpledialog.askstring("หมายเหตุผู้ใช้", f"ระบุหมายเหตุ/แจ้งปัญหา สำหรับรอบบิล {cycle_str}:")
        if comment is not None: 
            db.update_user_comment(self.current_user[0], month, year, comment.strip())
            messagebox.showinfo("Success", "บันทึกหมายเหตุของคุณเรียบร้อยแล้ว!")
            self.show_user_panel()

    def print_bill(self):
        selected = self.tree_user.selection()
        if not selected:
            messagebox.showwarning("เตือน", "เลือกบิลที่ต้องการพิมพ์")
            return
        item = self.tree_user.item(selected[0])['values']
        
        bill_text = f"""
        ====================================
               ใบแจ้งหนี้ค่าไฟฟ้า / น้ำประปา
        ====================================
        ผู้ใช้: {self.current_user[1]}
        ประจำเดือน: {item[0]}
        หน่วยที่ใช้งาน: {item[2]} หน่วย
        รวมเงินทั้งสิ้น: {float(item[3]):,.2f} บาท
        หมายเหตุจากแอดมิน: {item[4]}
        ====================================
        """
        messagebox.showinfo("พิมพ์บิล", bill_text)

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not filepath: return
        bills = db.get_user_bills(self.current_user[0])
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["รอบบิล", "มิเตอร์", "หน่วยที่ใช้", "ยอดเงิน", "การแก้ไข", "Admin Comment"])
            for b in bills:
                writer.writerow([f"{b[0]} {b[1]}", b[2], b[3], b[4], "Yes" if b[5] else "No", b[6]])
        messagebox.showinfo("Success", "Export เรียบร้อย!")

    def simulate_bill(self):
        units = simpledialog.askinteger("จำลอง", "ป้อนจำนวนหน่วยที่คาดว่าจะใช้:")
        if units:
            total = calculate_bill(units, self.current_user[3])
            messagebox.showinfo("ผลการจำลอง", f"ถ้าใช้ {units} หน่วย\nจะเสียค่าไฟประมาณ {total:,.2f} บาท")

if __name__ == "__main__":
    root = tk.Tk()
    app = BillApp(root)
    root.mainloop()