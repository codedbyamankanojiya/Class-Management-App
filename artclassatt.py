import sqlite3
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
from ttkbootstrap.dialogs import Messagebox
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
from tkinter import ttk
import winsound
import csv
from PIL import Image, ImageTk
import os
import calendar
import re
from collections import defaultdict

# Database Setup
conn = sqlite3.connect('students_attendance.db')
cursor = conn.cursor()

# Helper function to check if column exists
def column_exists(table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

# Create or alter the Students table
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS Students (
        roll_no TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
        dob TEXT,
        course_start_date TEXT,
        course_end_date TEXT
    )''')

# Add new columns if they don't exist
new_columns = [
    ("email", "TEXT"),
    ("fees_paid", "REAL DEFAULT 0"),
    ("total_fees", "REAL DEFAULT 0")
]

for col_name, col_type in new_columns:
    if not column_exists("Students", col_name):
        cursor.execute(f"ALTER TABLE Students ADD COLUMN {col_name} {col_type}")

conn.commit()

cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS attendance (
        roll_no TEXT,
        name TEXT,
        date TEXT,
        status TEXT,
        FOREIGN KEY(roll_no) REFERENCES students(roll_no)
    )''')
conn.commit()

# Functions
def play_sound(frequency=750, duration=300):
    winsound.Beep(frequency, duration)

def send_email_notification(to_email, subject, message):
    # Email functionality is disabled by default
    # To enable, configure these settings:
    ENABLE_EMAIL = False
    EMAIL_CONFIG = {
        "sender_email": "your-email@gmail.com",
        "password": "your-app-password",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587
    }
    
    if not ENABLE_EMAIL:
        return False
        
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender_email"]
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.starttls()
        server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["password"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def calculate_fees_status(roll_no):
    cursor.execute("""
        SELECT total_fees, fees_paid, course_end_date
        FROM students
        WHERE roll_no = ?
    """, (roll_no,))
    result = cursor.fetchone()
    
    if result:
        total_fees, fees_paid, end_date = result
        remaining = float(total_fees) - float(fees_paid)
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        days_left = (end_date - datetime.now().date()).days
        
        return {
            "total": total_fees,
            "paid": fees_paid,
            "remaining": remaining,
            "days_left": days_left,
            "status": "Completed" if remaining <= 0 else "Pending"
        }
    return None

def show_fees_details():
    # Get the current selection from the view_frame treeview
    treeview = None
    for child in view_frame.winfo_children():
        if isinstance(child, ttk.Treeview):
            treeview = child
            break
            
    if not treeview or not treeview.selection():
        messagebox.showwarning("Select Student", "Please select a student first!")
        return
        
    selected_item = treeview.selection()[0]
    roll_no = treeview.item(selected_item)["values"][0]
    student_name = treeview.item(selected_item)["values"][1]
    
    # Get complete student details including email
    cursor.execute("""
        SELECT email, total_fees, fees_paid, course_end_date 
        FROM students 
        WHERE roll_no = ?
    """, (roll_no,))
    
    student_data = cursor.fetchone()
    if not student_data:
        messagebox.showerror("Error", "Student not found in database!")
        return
        
    email, total_fees, fees_paid, course_end_date = student_data
    remaining = float(total_fees) - float(fees_paid)
    days_left = (datetime.strptime(course_end_date, "%Y-%m-%d").date() - datetime.now().date()).days
    status = "Completed" if remaining <= 0 else "Pending"
    
    # Create the fees window with better styling
    fees_window = tb.Toplevel(root)
    fees_window.title(f"Fees Management - {student_name} ({roll_no})")
    fees_window.geometry("500x450")
    
    # Main container
    main_frame = tb.Frame(fees_window, padding=20)
    main_frame.pack(fill='both', expand=True)
    
    # Header
    header_frame = tb.Frame(main_frame)
    header_frame.pack(fill='x', pady=(0, 20))
    
    tb.Label(header_frame, 
             text=f"Fees Management", 
             font=("Helvetica", 16, "bold"),
             bootstyle="primary").pack(anchor='w')
    
    # Student info section
    info_frame = tb.LabelFrame(main_frame, text="Student Information", padding=15)
    info_frame.pack(fill='x', pady=(0, 20))
    
    info_grid = tb.Frame(info_frame)
    info_grid.pack(fill='x')
    
    def add_info_row(label, value, row):
        lbl = tb.Label(info_grid, text=label, font=("Helvetica", 10, "bold"), width=15, anchor='w')
        lbl.grid(row=row, column=0, sticky='w', pady=2)
        val = tb.Label(info_grid, text=str(value), font=("Helvetica", 10))
        val.grid(row=row, column=1, sticky='w', pady=2, padx=5)
    
    add_info_row("Student:", f"{student_name} ({roll_no})", 0)
    add_info_row("Email:", email, 1)
    add_info_row("Course End Date:", course_end_date, 2)
    
    # Fees summary section
    summary_frame = tb.LabelFrame(main_frame, text="Fees Summary", padding=15)
    summary_frame.pack(fill='x', pady=(0, 20))
    
    # Styling for the summary
    style = tb.Style()
    style.configure('Fees.TLabel', font=('Helvetica', 11))
    style.configure('Amount.TLabel', font=('Helvetica', 11, 'bold'))
    
    # Create a grid for the summary
    summary_grid = tb.Frame(summary_frame)
    summary_grid.pack(fill='x')
    
    # Add summary rows
    def add_summary_row(label, value, row, style='Fees.TLabel'):
        lbl = tb.Label(summary_grid, text=label, style=style, width=15, anchor='w')
        lbl.grid(row=row, column=0, sticky='w', pady=3)
        val = tb.Label(summary_grid, text=f"₹{value:,.2f}", style='Amount.TLabel')
        val.grid(row=row, column=1, sticky='e', pady=3, padx=10)
    
    add_summary_row("Total Fees:", float(total_fees), 0)
    add_summary_row("Paid:", float(fees_paid), 1)
    
    # Calculate and show remaining with color coding
    remaining = float(total_fees) - float(fees_paid)
    remaining_style = 'success' if remaining <= 0 else 'danger' if remaining > 0 and days_left < 0 else 'warning'
    
    remaining_lbl = tb.Label(summary_grid, text="Remaining:", style='Fees.TLabel', width=15, anchor='w')
    remaining_lbl.grid(row=2, column=0, sticky='w', pady=3)
    remaining_val = tb.Label(summary_grid, text=f"₹{remaining:,.2f}", 
                           style=f'{remaining_style}.Inverse.TLabel',
                           padding=(10, 2))
    remaining_val.grid(row=2, column=1, sticky='e', pady=3, padx=10)
    
    # Status with days left
    status_text = f"{status}"
    if status == "Pending":
        status_text += f" ({abs(days_left)} days {'overdue' if days_left < 0 else 'left'})"
    
    status_lbl = tb.Label(summary_grid, text="Status:", style='Fees.TLabel', width=15, anchor='w')
    status_lbl.grid(row=3, column=0, sticky='w', pady=3)
    status_val = tb.Label(summary_grid, text=status_text, 
                         style=f'{remaining_style}.Inverse.TLabel',
                         padding=(10, 2))
    status_val.grid(row=3, column=1, sticky='e', pady=3, padx=10)
    
    # Payment form (only if fees are pending)
    if remaining > 0:
        payment_frame = tb.LabelFrame(main_frame, text="Record Payment", padding=15)
        payment_frame.pack(fill='x')
        
        amount_frame = tb.Frame(payment_frame)
        amount_frame.pack(fill='x', pady=10)
        
        tb.Label(amount_frame, text="Amount (₹):", width=15, anchor='w').pack(side='left')
        
        amount_var = tb.StringVar()
        amount_entry = tb.Entry(amount_frame, textvariable=amount_var,
                              validate='key', 
                              validatecommand=(fees_validate, '%P'),
                              width=15)
        amount_entry.pack(side='left', padx=5)
        
        # Add max button
        def set_max_amount():
            amount_var.set(f"{remaining:.2f}")
        
        max_btn = tb.Button(amount_frame, text="Full Amount", 
                          command=set_max_amount,
                          bootstyle="outline",
                          width=12)
        max_btn.pack(side='left', padx=5)
        
        # Payment date
        date_frame = tb.Frame(payment_frame)
        date_frame.pack(fill='x', pady=10)
        
        tb.Label(date_frame, text="Payment Date:", width=15, anchor='w').pack(side='left')
        
        today = datetime.now().strftime("%d/%m/%Y")
        date_entry = tb.DateEntry(date_frame, bootstyle="primary",
                                dateformat="%d/%m/%Y",
                                startdate=today)
        date_entry.pack(side='left', padx=5)
        
        # Payment method
        method_frame = tb.Frame(payment_frame)
        method_frame.pack(fill='x', pady=10)
        
        tb.Label(method_frame, text="Payment Method:", width=15, anchor='w').pack(side='left')
        
        method_var = tb.StringVar(value="Cash")
        methods = ["Cash", "Credit Card", "Bank Transfer", "UPI", "Cheque"]
        
        for method in methods:
            rb = tb.Radiobutton(method_frame, text=method, 
                              variable=method_var, 
                              value=method)
            rb.pack(side='left', padx=5)
        
        # Submit button
        def process_payment():
            try:
                amount = float(amount_var.get())
                if amount <= 0:
                    raise ValueError("Amount must be positive")
                    
                if amount > remaining:
                    raise ValueError(f"Amount cannot exceed remaining balance of ₹{remaining:,.2f}")
                
                payment_date = datetime.strptime(date_entry.entry.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
                payment_method = method_var.get()
                
                # Update fees paid in students table
                new_paid = float(fees_paid) + amount
                cursor.execute("""
                    UPDATE students
                    SET fees_paid = ?
                    WHERE roll_no = ?
                """, (new_paid, roll_no))
                
                # Record payment in payments table (create if not exists)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        roll_no TEXT,
                        amount REAL,
                        payment_date TEXT,
                        method TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(roll_no) REFERENCES students(roll_no)
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO payments (roll_no, amount, payment_date, method)
                    VALUES (?, ?, ?, ?)
                ''', (roll_no, amount, payment_date, payment_method))
                
                conn.commit()
                
                # Send payment receipt
                receipt_message = f"""
                Payment Receipt
                -----------------
                
                Student: {student_name}
                Roll No: {roll_no}
                Date: {payment_date}
                Amount: ₹{amount:,.2f}
                Method: {payment_method}
                
                Thank you for your payment!
                """
                
                if send_email_notification(email, "Payment Receipt", receipt_message):
                    messagebox.showinfo("Success", 
                        f"Payment of ₹{amount:,.2f} recorded successfully!\n"
                        f"Receipt has been sent to {email}.")
                else:
                    messagebox.showinfo("Success", 
                        f"Payment of ₹{amount:,.2f} recorded successfully!\n"
                        "(Email notification failed to send)")
                
                fees_window.destroy()
                view_students()  # Refresh the student list
                
            except ValueError as e:
                messagebox.showerror("Error", str(e))
        
        btn_frame = tb.Frame(payment_frame)
        btn_frame.pack(pady=(20, 5))
        
        tb.Button(btn_frame, text="Record Payment", 
                 command=process_payment,
                 bootstyle="success",
                 width=15).pack(side='left', padx=5)
        
        tb.Button(btn_frame, text="Print Receipt",
                 command=lambda: print_receipt(roll_no, student_name, email, 
                                             amount_var.get() or "0.00",
                                             date_entry.entry.get(),
                                             method_var.get()),
                 bootstyle="info",
                 width=15).pack(side='left', padx=5)
    
    # Add payment history section
    cursor.execute('''
        SELECT payment_date, amount, method 
        FROM payments 
        WHERE roll_no = ? 
        ORDER BY payment_date DESC 
        LIMIT 5
    ''', (roll_no,))
    
    payments = cursor.fetchall()
    
    if payments:
        history_frame = tb.LabelFrame(main_frame, text="Recent Payments", padding=15)
        history_frame.pack(fill='x', pady=(20, 0))
        
        # Create a treeview for payment history
        columns = ("Date", "Amount", "Method")
        tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=min(5, len(payments)))
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')
        
        # Add data
        for payment in payments:
            date, amount, method = payment
            tree.insert("", "end", values=(
                date,
                f"₹{float(amount):,.2f}",
                method
            ))
        
        tree.pack(fill='x')
        
        # Add view all payments button if there are more than 5
        if len(payments) >= 5:
            tb.Button(history_frame, 
                     text="View All Payments",
                     command=lambda: show_payment_history(roll_no, student_name),
                     bootstyle="link").pack(pady=(5, 0))

def print_receipt(roll_no, name, email, amount, date, method):
    """Generate a printable receipt"""
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Please enter a valid amount first")
            
        receipt = f"""
        ╔══════════════════════════════╗
        ║      ART CLASS PAYMENT       ║
        ╚══════════════════════════════╝
        
        Receipt No: {receipt_no:06d}
        Date: {date}
        
        Student: {name}
        Roll No: {roll_no}
        
        Amount: ₹{amount:,.2f}
        Method: {method}
        
        Thank you for your payment!
        
        {datetime.now().strftime('%d/%m/%Y %I:%M %p')}
        """.format(
            receipt_no=hash(f"{roll_no}{date}{amount}") % 1000000,
            name=name,
            roll_no=roll_no,
            amount=amount,
            date=date,
            method=method
        )
        
        # Show receipt in a messagebox
        messagebox.showinfo("Payment Receipt", receipt)
        
        # Option to email receipt
        if messagebox.askyesno("Email Receipt", "Would you like to email this receipt?"):
            if send_email_notification(email, "Payment Receipt - Art Class", receipt):
                messagebox.showinfo("Success", "Receipt has been sent to your email!")
            else:
                messagebox.showwarning("Email Failed", "Failed to send email. Please check your email settings.")
                
    except ValueError as e:
        messagebox.showerror("Error", str(e))

def show_payment_history(roll_no, student_name):
    """Show complete payment history for a student"""
    cursor.execute('''
        SELECT payment_date, amount, method 
        FROM payments 
        WHERE roll_no = ? 
        ORDER BY payment_date DESC
    ''', (roll_no,))
    
    payments = cursor.fetchall()
    
    if not payments:
        messagebox.showinfo("No Payments", "No payment history found for this student.")
        return
    
    history_window = tb.Toplevel(root)
    history_window.title(f"Payment History - {student_name} ({roll_no})")
    history_window.geometry("800x600")
    
    # Main frame
    main_frame = tb.Frame(history_window, padding=20)
    main_frame.pack(fill='both', expand=True)
    
    # Header
    tb.Label(main_frame, 
             text=f"Payment History - {student_name}", 
             font=("Helvetica", 14, "bold"),
             bootstyle="primary").pack(anchor='w', pady=(0, 20))
    
    # Summary frame
    summary_frame = tb.Frame(main_frame)
    summary_frame.pack(fill='x', pady=(0, 20))
    
    # Calculate totals
    total_paid = sum(p[1] for p in payments)
    
    # Get total fees from students table
    cursor.execute('SELECT total_fees FROM students WHERE roll_no = ?', (roll_no,))
    total_fees = cursor.fetchone()[0]
    
    # Summary labels
    tb.Label(summary_frame, 
             text=f"Total Fees: ₹{float(total_fees):,.2f}",
             font=("Helvetica", 12, "bold")).pack(side='left', padx=10)
    
    tb.Label(summary_frame, 
             text=f"Total Paid: ₹{total_paid:,.2f}",
             font=("Helvetica", 12, "bold"),
             bootstyle="success").pack(side='left', padx=10)
    
    remaining = float(total_fees) - total_paid
    remaining_style = "success" if remaining <= 0 else "danger" if remaining > 0 and any(p[0] < datetime.now().date().isoformat() for p in payments) else "warning"
    
    tb.Label(summary_frame, 
             text=f"Remaining: ₹{remaining:,.2f}",
             font=("Helvetica", 12, "bold"),
             bootstyle=remaining_style).pack(side='left', padx=10)
    
    # Treeview for payment history
    columns = ("Date", "Amount", "Payment Method", "Days Since Payment")
    tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=20)
    
    # Configure columns
    col_widths = {"Date": 120, "Amount": 100, "Payment Method": 150, "Days Since Payment": 120}
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=col_widths.get(col, 100), anchor='center')
    
    # Add data
    for payment in payments:
        payment_date = datetime.strptime(payment[0], "%Y-%m-%d").date()
        days_since = (datetime.now().date() - payment_date).days
        
        tree.insert("", "end", values=(
            payment[0],
            f"₹{float(payment[1]):,.2f}",
            payment[2],
            f"{days_since} days ago" if days_since > 0 else "Today" if days_since == 0 else "Future date"
        ))
    
    # Add scrollbars
    y_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
    x_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
    
    # Grid layout
    tree.pack(side='left', fill='both', expand=True)
    y_scrollbar.pack(side='right', fill='y')
    x_scrollbar.pack(side='bottom', fill='x')
    
    # Export button
    def export_payments():
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"payments_{roll_no}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Date", "Amount", "Payment Method"])
                    for payment in payments:
                        writer.writerow([payment[0], payment[1], payment[2]])
                messagebox.showinfo("Success", f"Payment history exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    btn_frame = tb.Frame(main_frame)
    btn_frame.pack(fill='x', pady=(10, 0))
    
    tb.Button(btn_frame, 
             text="Export to CSV", 
             command=export_payments,
             bootstyle="info").pack(side='left', padx=5)
    
    tb.Button(btn_frame, 
             text="Print Statement", 
             command=lambda: print_statement(roll_no, student_name, payments, total_fees),
             bootstyle="secondary").pack(side='left', padx=5)

def print_statement(roll_no, student_name, payments, total_fees):
    """Generate a printable statement of account"""
    statement = f"""
    ╔══════════════════════════════╗
    ║   STATEMENT OF ACCOUNT      ║
    ╚══════════════════════════════╝
    
    Student: {student_name}
    Roll No: {roll_no}
    
    As of: {datetime.now().strftime('%d %m %Y %I:%M %p')}
    
    {'-'*50}
    {'Date':<15} {'Description':<25} {'Amount':>10}
    {'-'*50}
    """
    
    # Add payments
    total_paid = 0
    for payment in payments:
        date, amount, method = payment
        statement += f"{date:<15} {'Payment (' + method + ')':<25} {float(amount):>10,.2f}\n"
        total_paid += float(amount)
    
    statement += f"{'='*50}\n"
    statement += f"{'Total Fees:':<40} {float(total_fees):>10,.2f}\n"
    statement += f"{'Total Paid:':<40} {total_paid:>10,.2f}\n"
    statement += f"{'Balance:':<40} {(float(total_fees) - total_paid):>10,.2f}\n"
    statement += f"{'='*50}\n"
    
    # Show statement in a messagebox
    messagebox.showinfo("Account Statement", statement)
    
    # Option to print or save as text file
    if messagebox.askyesno("Save Statement", "Would you like to save this statement to a file?"):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"statement_{roll_no}_{datetime.now().strftime('%Y%m%d')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(statement)
                messagebox.showinfo("Success", f"Statement saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

def export_to_csv(data, filename):
    try:
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)
        return True
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export data: {e}")
        return False

def generate_monthly_report():
    month = datetime.now().month
    year = datetime.now().year
    
    report_window = tb.Toplevel(root)
    report_window.title(f"Monthly Attendance Report - {calendar.month_name[month]} {year}")
    report_window.geometry("1000x700")
    
    frame = ScrolledFrame(report_window)
    frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Create statistics view
    stats_frame = tb.LabelFrame(frame, text="Monthly Statistics", padding=15)
    stats_frame.pack(fill='x', pady=(0, 10))
    
    # Calculate statistics
    cursor.execute("""
        SELECT roll_no, COUNT(*) as present_days 
        FROM attendance 
        WHERE strftime('%Y-%m', date) = ? 
        GROUP BY roll_no
    """, (f"{year}-{month:02d}",))
    
    attendance_data = cursor.fetchall()
    total_days = calendar.monthrange(year, month)[1]
    
    # Display statistics in a grid
    headers = ["Roll No", "Student Name", "Present Days", "Attendance %"]
    tree = ttk.Treeview(stats_frame, columns=headers, show='headings')
    
    for header in headers:
        tree.heading(header, text=header)
        tree.column(header, width=150)
    
    for roll_no, present_days in attendance_data:
        cursor.execute("SELECT name FROM students WHERE roll_no = ?", (roll_no,))
        name = cursor.fetchone()[0]
        attendance_percent = (present_days / total_days) * 100
        
        tree.insert("", "end", values=(
            roll_no,
            name,
            present_days,
            f"{attendance_percent:.1f}%"
        ))
    
    tree.pack(fill='both', expand=True)
    
    # Export button
    def export_report():
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"attendance_report_{year}_{month}.csv"
        )
        if filename:
            data = [headers]  # Add headers first
            for item in tree.get_children():
                data.append(tree.item(item)['values'])
            if export_to_csv(data, filename):
                messagebox.showinfo("Success", "Report exported successfully!")
    
    tb.Button(frame, text="Export to CSV", 
              command=export_report,
              bootstyle="info-outline").pack(pady=10)

def show_student_profile(roll_no):
    cursor.execute("""
        SELECT s.*, 
               COUNT(a.date) as total_present,
               (SELECT COUNT(DISTINCT date) FROM attendance) as total_days
        FROM students s
        LEFT JOIN attendance a ON s.roll_no = a.roll_no
        WHERE s.roll_no = ?
        GROUP BY s.roll_no
    """, (roll_no,))
    
    student = cursor.fetchone()
    if not student:
        messagebox.showerror("Error", "Student not found!")
        return
    
    profile_window = tb.Toplevel(root)
    profile_window.title(f"Student Profile - {student[1]}")
    profile_window.geometry("800x600")
    
    main_frame = tb.Frame(profile_window)
    main_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Header
    header = tb.Label(main_frame, 
                     text=f"Student Profile: {student[1]}",
                     font=("Helvetica", 18, "bold"))
    header.pack(pady=(0, 20))
    
    # Details frame
    details_frame = tb.Labelframe(main_frame, text="Student Details", padding=15)
    details_frame.pack(fill='x', pady=(0, 20))
    
    details = [
        ("Roll Number:", student[0]),
        ("Name:", student[1]),
        ("Phone:", student[2]),
        ("Date of Birth:", datetime.strptime(student[3], "%Y-%m-%d").strftime("%d %B %Y")),
        ("Course Duration:", f"{student[4]} to {student[5]}"),
        ("Attendance Rate:", f"{(student[6]/student[7]*100 if student[7] else 0):.1f}%")
    ]
    
    for label, value in details:
        row = tb.Frame(details_frame)
        row.pack(fill='x', pady=5)
        tb.Label(row, text=label, font=("Helvetica", 11, "bold")).pack(side='left')
        tb.Label(row, text=str(value), font=("Helvetica", 11)).pack(side='left', padx=(10, 0))
    
    # Attendance History
    history_frame = tb.Labelframe(main_frame, text="Recent Attendance", padding=15)
    history_frame.pack(fill='both', expand=True)
    
    tree = ttk.Treeview(history_frame, columns=("Date", "Status"), show='headings')
    tree.heading("Date", text="Date")
    tree.heading("Status", text="Status")
    
    cursor.execute("""
        SELECT date, status 
        FROM attendance 
        WHERE roll_no = ? 
        ORDER BY date DESC 
        LIMIT 10
    """, (roll_no,))
    
    for date, status in cursor.fetchall():
        tree.insert("", 0, values=(date, status))
    
    tree.pack(fill='both', expand=True)

def search_students(search_term):
    cursor.execute("""
        SELECT * FROM students 
        WHERE roll_no LIKE ? OR name LIKE ? OR phone LIKE ?
    """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
    
    rows = cursor.fetchall()
    return rows

def create_custom_style():
    style = ttk.Style()
    
    # Configure color scheme
    primary_color = "#2b2b2b"
    secondary_color = "#404040"
    accent_color = "#007bff"
    text_color = "white"
    
    # Configure Treeview
    style.configure("Treeview",
                   background=primary_color,
                   foreground=text_color,
                   fieldbackground=primary_color,
                   borderwidth=0,
                   rowheight=30)
    
    style.configure("Treeview.Heading",
                   background=secondary_color,
                   foreground=text_color,
                   relief="flat",
                   font=("Helvetica", 10, "bold"))
    
    style.map("Treeview.Heading",
              background=[('active', accent_color)])
    
    style.map("Treeview",
              background=[('selected', accent_color)],
              foreground=[('selected', 'white')])
    
    # Configure other widgets
    style.configure("TEntry", padding=8, font=("Helvetica", 10))
    style.configure("TButton", 
                   padding=(15, 10),
                   font=("Helvetica", 10, "bold"))
    
    style.configure("Primary.TButton",
                   background=accent_color,
                   foreground="white")
    
    style.configure("Custom.TLabelframe", 
                   background=primary_color,
                   borderwidth=2,
                   relief="solid")
    
    style.configure("Custom.TLabelframe.Label",
                   foreground=text_color,
                   background=primary_color,
                   font=("Helvetica", 12, "bold"))
    
    # Configure DateEntry
    style.configure("DateEntry",
                   background=primary_color,
                   foreground=text_color,
                   arrowcolor=text_color)
                   
    # Configure Search Entry
    style.configure("Search.TEntry",
                   padding=10,
                   font=("Helvetica", 11))

def mark_attendance():
    roll_no = entry_roll.get().strip()
    date = datetime.now().strftime("%Y-%m-%d")

    if not roll_no:
        messagebox.showwarning("Input Error", "Please enter Roll Number.")
        return

    cursor.execute('SELECT * FROM attendance WHERE roll_no = ? AND date = ?', (roll_no, date))
    if cursor.fetchone():
        messagebox.showinfo("Already Marked", "Attendance already marked for today!")
        return

    cursor.execute('SELECT course_end_date, name FROM students WHERE roll_no = ?', (roll_no,))
    result = cursor.fetchone()

    if result:
        course_end_date = datetime.strptime(result[0], "%Y-%m-%d")
        today = datetime.now()

        if today.date() > course_end_date.date():
            messagebox.showerror("Course Ended", "Your course has ended!")
            play_sound(frequency=1000, duration=500)
        else:
            try:
                cursor.execute('INSERT INTO attendance (roll_no, name, date, status) VALUES (?, ?, ?, ?)',
                               (roll_no, result[1], date, "Present"))
                conn.commit()
                messagebox.showinfo("Success", f"Attendance marked for Roll No {roll_no}")
                play_sound()
                entry_roll.delete(0, tb.END)
                entry_roll.focus_set()
                view_today_attendance()  # Refresh attendance view
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to mark attendance: {e}")
    else:
        messagebox.showwarning("Error", "Student not found!")
        entry_roll.delete(0, tb.END)
        entry_roll.focus_set()

def add_student():
    roll_no = entry_roll_add.get().strip()
    name = entry_name.get().strip()
    phone = entry_phone.get().strip()
    email = entry_email.get().strip()
    dob = entry_dob.get().strip()
    course_start_date = entry_start.get().strip()
    course_end_date = entry_end.get().strip()
    total_fees = entry_fees.get().strip() or "0"
    fees_paid = entry_fees_paid.get().strip() or "0"

    # Validate required fields
    if not all([roll_no, name, phone, email, dob, course_start_date, course_end_date]):
        messagebox.showwarning("Input Error", "Please fill in all required fields.")
        return
        
    # Validate email format
    if not validate_email(email):
        messagebox.showerror("Invalid Email", "Please enter a valid email address.")
        return
        
    try:
        total_fees = float(total_fees)
        fees_paid = float(fees_paid)
        if fees_paid > total_fees:
            messagebox.showerror("Invalid Fees", "Paid amount cannot exceed total fees.")
            return
    except ValueError:
        messagebox.showerror("Invalid Fees", "Please enter valid amounts for fees.")
        return

    try:
        dob = datetime.strptime(dob, "%d/%m/%Y").strftime("%Y-%m-%d")
        course_start_date = datetime.strptime(course_start_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        course_end_date = datetime.strptime(course_end_date, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Date Error", "Dates must be in DD/MM/YYYY format.")
        return

    try:
        cursor.execute('''
            INSERT INTO students 
            (roll_no, name, phone, email, dob, course_start_date, course_end_date, total_fees, fees_paid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (roll_no, name, phone, email, dob, course_start_date, course_end_date, total_fees, fees_paid))
        conn.commit()
        
        # Send welcome email
        email_message = f"""
        Welcome to Art Class!
        
        Dear {name},
        
        Your registration has been completed successfully.
        
        Registration Details:
        Roll Number: {roll_no}
        Course Duration: {course_start_date} to {course_end_date}
        Total Fees: ₹{total_fees}
        Amount Paid: ₹{fees_paid}
        
        Thank you for joining us!
        """
        
        if send_email_notification(email, "Welcome to Art Class", email_message):
            messagebox.showinfo("Success", "Student added successfully and welcome email sent!")
        else:
            messagebox.showinfo("Success", "Student added successfully (email notification failed)")
            
        clear_entries()
        entry_roll_add.focus_set()
        view_students()  # Refresh student list
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Roll Number already exists!")

def update_student_view(rows):
    for widget in view_frame.winfo_children():
        widget.destroy()

    columns = ("Roll No", "Name", "Phone", "DOB", "Course Start Date", "Course End Date", "Status")
    tree = ttk.Treeview(view_frame, columns=columns, show='headings', style="Treeview")
    
    # Configure columns
    column_widths = {
        "Roll No": 100,
        "Name": 200,
        "Phone": 120,
        "DOB": 120,
        "Course Start Date": 120,
        "Course End Date": 120,
        "Status": 100
    }
    
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_treeview(tree, c, False))
        tree.column(col, width=column_widths[col])

    # Add scrollbars
    y_scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=tree.yview)
    x_scrollbar = ttk.Scrollbar(view_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
    
    # Grid layout
    tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    y_scrollbar.grid(row=0, column=1, sticky="ns")
    x_scrollbar.grid(row=1, column=0, sticky="ew")
    
    view_frame.grid_columnconfigure(0, weight=1)
    view_frame.grid_rowconfigure(0, weight=1)
    
    # Populate data with status
    today = datetime.now().date()
    for row in rows:
        course_end = datetime.strptime(row[5], "%Y-%m-%d").date()
        days_left = (course_end - today).days
        
        if days_left < 0:
            status = "Expired"
            tags = ("expired",)
        elif days_left <= 7:
            status = f"{days_left}d left"
            tags = ("warning",)
        else:
            status = "Active"
            tags = ("active",)
        
        values = list(row) + [status]
        tree.insert("", tb.END, values=values, tags=tags)
    
    # Configure tags
    tree.tag_configure("expired", foreground="#ff4444")
    tree.tag_configure("warning", foreground="#ffbb33")
    tree.tag_configure("active", foreground="#00C851")
    
    # Bind double-click event
    tree.bind("<Double-1>", lambda e: show_student_profile(
        tree.item(tree.selection()[0])["values"][0] if tree.selection() else None
    ))
    
    view_frame.pack(expand=True, fill='both', pady=10, padx=10)

def sort_treeview(tree, col, reverse):
    """Sort treeview by column."""
    l = [(tree.set(k, col), k) for k in tree.get_children("")]
    l.sort(reverse=reverse)
    
    # Rearrange items in sorted positions
    for index, (val, k) in enumerate(l):
        tree.move(k, "", index)
    
    # Reverse sort next time
    tree.heading(col, command=lambda: sort_treeview(tree, col, not reverse))

def view_students():
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    update_student_view(rows)

def view_today_attendance():
    today = datetime.now().strftime("%Y-%m-%d")
    
    attendance_window = tb.Toplevel(root)
    attendance_window.title("Today's Attendance")
    attendance_window.geometry("800x600")

    frame = ScrolledFrame(attendance_window)
    frame.pack(fill='both', expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=("Roll No", "Name", "Date", "Status"), show='headings', style="Treeview")
    for col in ("Roll No", "Name", "Date", "Status"):
        tree.heading(col, text=col)
        tree.column(col, width=150)

    tree.pack(fill='both', expand=True, padx=5, pady=5)

    cursor.execute("SELECT roll_no, name, date, status FROM attendance WHERE date = ?", (today,))
    rows = cursor.fetchall()
    for row in rows:
        tree.insert("", tb.END, values=row)

def view_expiring_courses():
    today = datetime.now().date()

    expiring_window = tb.Toplevel(root)
    expiring_window.title("Expiring Courses")
    expiring_window.geometry("800x600")

    frame = ScrolledFrame(expiring_window)
    frame.pack(fill='both', expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=("Roll No", "Name", "Course End Date", "Days Left"), show='headings', style="Treeview")
    for col in ("Roll No", "Name", "Course End Date", "Days Left"):
        tree.heading(col, text=col)
        tree.column(col, width=150)

    cursor.execute("SELECT roll_no, name, course_end_date FROM students")
    rows = cursor.fetchall()
    for row in rows:
        course_end_date = datetime.strptime(row[2], "%Y-%m-%d").date()
        days_left = (course_end_date - today).days
        if 0 <= days_left <= 7:  # Show courses expiring within a week
            status_color = "red" if days_left <= 3 else "orange"
            tree.insert("", tb.END, values=(row[0], row[1], row[2], f"{days_left} days"), tags=(status_color,))
            tree.tag_configure("red", foreground="#ff4444")
            tree.tag_configure("orange", foreground="#ffbb33")

    tree.pack(fill='both', expand=True, padx=5, pady=5)

def clear_entries():
    entry_roll_add.delete(0, tb.END)
    entry_name.delete(0, tb.END)
    entry_phone.delete(0, tb.END)
    entry_email.delete(0, tb.END)
    entry_fees.delete(0, tb.END)
    entry_fees_paid.delete(0, tb.END)
    entry_dob.delete(0, tb.END)
    entry_start.delete(0, tb.END)
    entry_end.delete(0, tb.END)

# GUI Setup
root = tb.Window(themename="darkly")
root.title("🎨 Art Class Attendance System")
root.geometry("1600x950")
root.state('zoomed')  # Start maximized
create_custom_style()

# Add status bar at bottom
status_bar = tb.Frame(root, bootstyle="dark")
status_bar.pack(side='bottom', fill='x')

status_label = tb.Label(status_bar, text="Ready", font=("Helvetica", 9))
status_label.pack(side='left', padx=10, pady=5)

time_label = tb.Label(status_bar, text="", font=("Helvetica", 9))
time_label.pack(side='right', padx=10, pady=5)

def update_time():
    current_time = datetime.now().strftime("%d %B %Y, %I:%M:%S %p")
    time_label.config(text=current_time)
    root.after(1000, update_time)

update_time()

# Create notebook for tabbed interface
notebook = tb.Notebook(root, bootstyle="primary")
notebook.pack(fill='both', expand=True, padx=10, pady=10)

# Tab 1: Dashboard
dashboard_tab = tb.Frame(notebook)
notebook.add(dashboard_tab, text="📊 Dashboard")

# Tab 2: Students
students_tab = tb.Frame(notebook)
notebook.add(students_tab, text="👥 Students")

# Tab 3: Attendance
attendance_tab = tb.Frame(notebook)
notebook.add(attendance_tab, text="✓ Attendance")

# Tab 4: Reports
reports_tab = tb.Frame(notebook)
notebook.add(reports_tab, text="📈 Reports")

# Tab 5: Fees
fees_tab = tb.Frame(notebook)
notebook.add(fees_tab, text="💰 Fees")

# ==================== DASHBOARD TAB ====================
dashboard_container = tb.Frame(dashboard_tab)
dashboard_container.pack(fill='both', expand=True, padx=20, pady=20)

# Dashboard Header
dash_header = tb.Label(dashboard_container, 
                       text="📊 Dashboard Overview",
                       font=("Helvetica", 24, "bold"),
                       bootstyle="inverse-primary")
dash_header.pack(pady=(0, 20))

# Statistics Cards Row
stats_frame = tb.Frame(dashboard_container)
stats_frame.pack(fill='x', pady=(0, 20))

def create_stat_card(parent, title, value, icon, color):
    card = tb.Frame(parent, bootstyle=f"{color}")
    card.pack(side='left', fill='both', expand=True, padx=10)
    
    inner = tb.Frame(card, bootstyle=f"{color}")
    inner.pack(fill='both', expand=True, padx=20, pady=20)
    
    tb.Label(inner, text=icon, font=("Helvetica", 36), 
             bootstyle=f"{color}").pack()
    tb.Label(inner, text=str(value), font=("Helvetica", 32, "bold"),
             bootstyle=f"{color}").pack()
    tb.Label(inner, text=title, font=("Helvetica", 12),
             bootstyle=f"{color}").pack()
    
    return card

# Get statistics
cursor.execute("SELECT COUNT(*) FROM students")
total_students = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT roll_no) FROM attendance WHERE date = ?", 
               (datetime.now().strftime("%Y-%m-%d"),))
today_attendance = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM students WHERE course_end_date >= ?",
               (datetime.now().strftime("%Y-%m-%d"),))
active_courses = cursor.fetchone()[0]

cursor.execute("SELECT SUM(total_fees - fees_paid) FROM students")
pending_fees = cursor.fetchone()[0] or 0

create_stat_card(stats_frame, "Total Students", total_students, "👥", "info")
create_stat_card(stats_frame, "Today's Attendance", today_attendance, "✓", "success")
create_stat_card(stats_frame, "Active Courses", active_courses, "📚", "primary")
create_stat_card(stats_frame, f"Pending Fees (₹{pending_fees:,.0f})", 
                f"{pending_fees:,.0f}", "💰", "warning")

# Recent Activity Section
activity_frame = tb.Labelframe(dashboard_container, text="📋 Recent Activity", 
                              padding=20, bootstyle="info")
activity_frame.pack(fill='both', expand=True, pady=(0, 10))

activity_tree = ttk.Treeview(activity_frame, 
                            columns=("Time", "Activity", "Details"), 
                            show='headings', height=10)
activity_tree.heading("Time", text="Time")
activity_tree.heading("Activity", text="Activity")
activity_tree.heading("Details", text="Details")
activity_tree.column("Time", width=150)
activity_tree.column("Activity", width=200)
activity_tree.column("Details", width=400)

# Get recent attendance
cursor.execute("""
    SELECT date, name, roll_no 
    FROM attendance 
    ORDER BY date DESC, rowid DESC 
    LIMIT 10
""")
for date, name, roll_no in cursor.fetchall():
    activity_tree.insert("", "end", values=(
        date, 
        "Attendance Marked", 
        f"{name} (Roll: {roll_no})"
    ))

activity_tree.pack(fill='both', expand=True)

# Quick Actions in Dashboard
quick_dash_frame = tb.Frame(dashboard_container)
quick_dash_frame.pack(fill='x', pady=(10, 0))

tb.Button(quick_dash_frame, text="🚀 Mark Attendance",
         command=lambda: notebook.select(2),
         bootstyle="success", width=20).pack(side='left', padx=5)

tb.Button(quick_dash_frame, text="➕ Add Student",
         command=lambda: notebook.select(1),
         bootstyle="info", width=20).pack(side='left', padx=5)

tb.Button(quick_dash_frame, text="📊 View Reports",
         command=lambda: notebook.select(3),
         bootstyle="primary", width=20).pack(side='left', padx=5)

# ==================== STUDENTS TAB ====================
main_container = tb.Frame(students_tab)
main_container.pack(fill='both', expand=True, padx=20, pady=20)

# Add keyboard shortcuts
root.bind("<Control-a>", lambda e: view_today_attendance())
root.bind("<Control-r>", lambda e: generate_monthly_report())
root.bind("<Control-f>", lambda e: search_entry.focus_set())

# Header section with search
header_frame = tb.Frame(main_container)
header_frame.pack(fill='x', pady=(0, 20))

# Title with decorative elements
title_frame = tb.Frame(header_frame)
title_frame.pack(fill='x')

title_label = tb.Label(title_frame, text="👥 Student Management", 
                      font=("Helvetica", 20, "bold"),
                      bootstyle="inverse-info")
title_label.pack(pady=10)

# Custom Entry with placeholder
class PlaceholderEntry(tb.Entry):
    def __init__(self, container, placeholder, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = 'grey'
        self.default_fg_color = self['foreground']
        
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        
        self._add_placeholder()

    def _clear_placeholder(self, e):
        if self["foreground"] == self.placeholder_color:
            self.delete(0, tb.END)
            self["foreground"] = self.default_fg_color

    def _add_placeholder(self, e=None):
        if not self.get():
            self.insert(0, self.placeholder)
            self["foreground"] = self.placeholder_color
            
    def get(self):
        """Return the text or empty string if showing placeholder"""
        text = super().get()
        if text == self.placeholder and self["foreground"] == self.placeholder_color:
            return ""
        return text

# Search bar
search_frame = tb.Frame(header_frame)
search_frame.pack(fill='x', pady=(10, 0))

search_entry = PlaceholderEntry(
    search_frame,
    placeholder="Search by Roll No, Name or Phone...",
    font=("Helvetica", 11),
    bootstyle="secondary",
    width=40
)
search_entry.pack(side='left', padx=(0, 10))

def perform_search():
    search_term = search_entry.get().strip()
    if search_term:
        results = search_students(search_term)
        update_student_view(results)
    else:
        view_students()

search_button = tb.Button(search_frame, 
                         text="Search",
                         command=perform_search,
                         bootstyle="secondary-outline")
search_button.pack(side='left')

# Quick Actions Bar
actions_frame = tb.Frame(header_frame)
actions_frame.pack(fill='x', pady=(10, 0))

# Student count display
cursor.execute("SELECT COUNT(*) FROM students")
student_count = cursor.fetchone()[0]
count_label = tb.Label(actions_frame, 
                       text=f"Total Students: {student_count}",
                       font=("Helvetica", 12, "bold"),
                       bootstyle="inverse-success")
count_label.pack(side='left', padx=10)

tb.Button(actions_frame, text="🔄 Refresh",
         command=view_students,
         bootstyle="secondary-outline").pack(side='left', padx=5)

tb.Button(actions_frame, text="📤 Export to CSV",
         command=lambda: export_students_csv(),
         bootstyle="info-outline").pack(side='left', padx=5)

def export_students_csv():
    filename = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile=f"students_{datetime.now().strftime('%Y%m%d')}.csv"
    )
    if filename:
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Roll No", "Name", "Phone", "DOB", "Start Date", "End Date", "Email", "Fees Paid", "Total Fees"])
                writer.writerows(students)
            messagebox.showinfo("Success", f"Students exported to {filename}")
            status_label.config(text=f"Exported {len(students)} students")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

# Create left and right panels
left_panel = tb.Frame(main_container)
left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))

right_panel = tb.Frame(main_container)
right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))

# Mark Attendance Section (Left Panel)
frame_attendance = tb.Labelframe(left_panel, text="Quick Attendance", 
                               padding=15, bootstyle="primary")
frame_attendance.pack(fill='x', pady=(0, 10))

tb.Label(frame_attendance, text="Enter Roll Number:", 
         font=("Helvetica", 12)).pack(pady=(0, 5))
entry_roll = tb.Entry(frame_attendance, font=("Helvetica", 14))
entry_roll.pack(fill='x', pady=(0, 10))
entry_roll.bind("<Return>", lambda e: mark_attendance())

btn_mark = tb.Button(frame_attendance, text="Mark Attendance", 
                    command=mark_attendance, bootstyle="success-outline",
                    width=20)
btn_mark.pack(pady=5)

# Add Student Section (Left Panel)
frame_add = tb.Labelframe(left_panel, text="Add New Student", 
                         padding=15, bootstyle="primary")
frame_add.pack(fill='x', pady=10)

# Create two columns for better layout
left_column = tb.Frame(frame_add)
left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))

right_column = tb.Frame(frame_add)
right_column.pack(side='left', fill='both', expand=True, padx=(10, 0))

# Validation functions
def validate_phone(P):
    return len(P) <= 10 and (P.isdigit() or P == "")

def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_fees(P):
    try:
        if P == "": return True
        float(P)
        return True
    except ValueError:
        return False

phone_validate = root.register(validate_phone)
fees_validate = root.register(validate_fees)

# Left column fields
fields_left = [
    ("Roll Number:", "entry_roll_add", tb.Entry, {"font": ("Helvetica", 12)}),
    ("Name:", "entry_name", tb.Entry, {"font": ("Helvetica", 12)}),
    ("Phone Number:", "entry_phone", tb.Entry, {
        "font": ("Helvetica", 12),
        "validate": "key",
        "validatecommand": (phone_validate, "%P")
    }),
    ("Email:", "entry_email", tb.Entry, {"font": ("Helvetica", 12)}),
    ("Course Fees:", "entry_fees", tb.Entry, {
        "font": ("Helvetica", 12),
        "validate": "key",
        "validatecommand": (fees_validate, "%P")
    }),
    ("Fees Paid:", "entry_fees_paid", tb.Entry, {
        "font": ("Helvetica", 12),
        "validate": "key",
        "validatecommand": (fees_validate, "%P")
    })
]

# Right column fields with Entry
fields_right = [
    ("Date of Birth (DD/MM/YYYY):", "entry_dob", tb.Entry, {
        "font": ("Helvetica", 12)
    }),
    ("Course Start Date (DD/MM/YYYY):", "entry_start", tb.Entry, {
        "font": ("Helvetica", 12)
    }),
    ("Course End Date (DD/MM/YYYY):", "entry_end", tb.Entry, {
        "font": ("Helvetica", 12)
    })
]

entries = {}

# Create left column fields
for label_text, var_name, widget_class, widget_args in fields_left:
    field_frame = tb.Frame(left_column)
    field_frame.pack(fill='x', pady=5)
    
    tb.Label(field_frame, text=label_text, 
             font=("Helvetica", 10, "bold")).pack(anchor='w')
    entries[var_name] = widget_class(field_frame, **widget_args)
    entries[var_name].pack(fill='x', pady=(2, 5))

# Create right column fields
for label_text, var_name, widget_class, widget_args in fields_right:
    field_frame = tb.Frame(right_column)
    field_frame.pack(fill='x', pady=5)
    
    tb.Label(field_frame, text=label_text, 
             font=("Helvetica", 10, "bold")).pack(anchor='w')
    entries[var_name] = widget_class(field_frame, **widget_args)
    entries[var_name].pack(fill='x', pady=(2, 5))

entry_roll_add = entries["entry_roll_add"]
entry_name = entries["entry_name"]
entry_phone = entries["entry_phone"]
entry_email = entries["entry_email"]
entry_fees = entries["entry_fees"]
entry_fees_paid = entries["entry_fees_paid"]
entry_dob = entries["entry_dob"]
entry_start = entries["entry_start"]
entry_end = entries["entry_end"]

btn_add = tb.Button(frame_add, text="Add Student", 
                   command=add_student, bootstyle="info-outline",
                   width=20)
btn_add.pack(pady=10)

# View Frame for Students (Right Panel)
view_frame = tb.Labelframe(right_panel, text="Student Records", 
                          padding=15, bootstyle="primary")

# Report Buttons
btn_frame = tb.Frame(right_panel)
btn_frame.pack(pady=10)

btn_view_students = tb.Button(btn_frame, text="View Students", 
                            command=view_students, bootstyle="info",
                            width=20)
btn_view_students.pack(side='left', padx=5)

btn_view_attendance = tb.Button(btn_frame, text="Today's Attendance", 
                              command=view_today_attendance, bootstyle="warning",
                              width=20)
btn_view_attendance.pack(side='left', padx=5)

btn_view_expiring = tb.Button(btn_frame, text="Expiring Courses", 
                             command=view_expiring_courses, bootstyle="danger",
                             width=20)
btn_view_expiring.pack(side='left', padx=5)

# Add Fees Management Button
btn_fees = tb.Button(btn_frame, text="Fees Management", 
                    command=lambda: show_fees_details() if view_frame.winfo_children() else None,
                    bootstyle="secondary",
                    width=20)
btn_fees.pack(side='left', padx=5)

def check_pending_fees():
    """Check and notify students with pending fees"""
    cursor.execute("""
        SELECT roll_no, name, email, total_fees, fees_paid, course_end_date
        FROM students
        WHERE total_fees > fees_paid
    """)
    
    for student in cursor.fetchall():
        roll_no, name, email, total, paid, end_date = student
        remaining = float(total) - float(paid)
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        days_left = (end_date - datetime.now().date()).days
        
        if days_left <= 7 and remaining > 0:
            message = f"""
            Dear {name},
            
            This is a reminder that you have pending fees of ₹{remaining}.
            Your course will end in {days_left} days.
            
            Please clear your dues as soon as possible.
            
            Thank you!
            """
            
            send_email_notification(email, "Fees Payment Reminder", message)

# Schedule periodic fees check (every 24 hours)
def schedule_fees_check():
    check_pending_fees()
    root.after(24*60*60*1000, schedule_fees_check)  # 24 hours in milliseconds

schedule_fees_check()

# ==================== ATTENDANCE TAB ====================
attendance_container = tb.Frame(attendance_tab)
attendance_container.pack(fill='both', expand=True, padx=20, pady=20)

# Attendance Header
att_header = tb.Label(attendance_container, 
                      text="✓ Attendance Management",
                      font=("Helvetica", 20, "bold"),
                      bootstyle="inverse-success")
att_header.pack(pady=(0, 20))

# Quick Mark Attendance
quick_att_frame = tb.Labelframe(attendance_container, text="Quick Mark Attendance", 
                               padding=20, bootstyle="success")
quick_att_frame.pack(fill='x', pady=(0, 20))

att_input_frame = tb.Frame(quick_att_frame)
att_input_frame.pack(fill='x')

tb.Label(att_input_frame, text="Roll Number:", 
         font=("Helvetica", 12, "bold")).pack(side='left', padx=(0, 10))
att_entry = tb.Entry(att_input_frame, font=("Helvetica", 14), width=20)
att_entry.pack(side='left', padx=(0, 10))
att_entry.bind("<Return>", lambda e: mark_attendance_from_tab())

def mark_attendance_from_tab():
    roll_no = att_entry.get().strip()
    date = datetime.now().strftime("%Y-%m-%d")

    if not roll_no:
        messagebox.showwarning("Input Error", "Please enter Roll Number.")
        return

    cursor.execute('SELECT * FROM attendance WHERE roll_no = ? AND date = ?', (roll_no, date))
    if cursor.fetchone():
        messagebox.showinfo("Already Marked", "Attendance already marked for today!")
        return

    cursor.execute('SELECT course_end_date, name FROM students WHERE roll_no = ?', (roll_no,))
    result = cursor.fetchone()

    if result:
        course_end_date = datetime.strptime(result[0], "%Y-%m-%d")
        today = datetime.now()

        if today.date() > course_end_date.date():
            messagebox.showerror("Course Ended", "Course has ended!")
            play_sound(frequency=1000, duration=500)
        else:
            try:
                cursor.execute('INSERT INTO attendance (roll_no, name, date, status) VALUES (?, ?, ?, ?)',
                               (roll_no, result[1], date, "Present"))
                conn.commit()
                messagebox.showinfo("Success", f"Attendance marked for {result[1]}")
                play_sound()
                att_entry.delete(0, tb.END)
                att_entry.focus_set()
                refresh_today_attendance()
                status_label.config(text=f"Attendance marked for {result[1]}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to mark attendance: {e}")
    else:
        messagebox.showwarning("Error", "Student not found!")
        att_entry.delete(0, tb.END)

tb.Button(att_input_frame, text="Mark Present",
         command=mark_attendance_from_tab,
         bootstyle="success", width=15).pack(side='left', padx=5)

# Today's Attendance Display
today_att_frame = tb.Labelframe(attendance_container, text=f"Today's Attendance ({datetime.now().strftime('%d %B %Y')})", 
                               padding=20, bootstyle="info")
today_att_frame.pack(fill='both', expand=True)

today_att_tree = ttk.Treeview(today_att_frame, 
                             columns=("Roll No", "Name", "Time", "Status"), 
                             show='headings', height=15)
today_att_tree.heading("Roll No", text="Roll No")
today_att_tree.heading("Name", text="Name")
today_att_tree.heading("Time", text="Time")
today_att_tree.heading("Status", text="Status")
today_att_tree.column("Roll No", width=100)
today_att_tree.column("Name", width=250)
today_att_tree.column("Time", width=150)
today_att_tree.column("Status", width=100)

def refresh_today_attendance():
    for item in today_att_tree.get_children():
        today_att_tree.delete(item)
    
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT roll_no, name, date, status FROM attendance WHERE date = ?", (today,))
    for row in cursor.fetchall():
        today_att_tree.insert("", "end", values=(row[0], row[1], row[2], row[3]))

refresh_today_attendance()

scrollbar = ttk.Scrollbar(today_att_frame, orient="vertical", command=today_att_tree.yview)
today_att_tree.configure(yscrollcommand=scrollbar.set)
today_att_tree.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')

# ==================== REPORTS TAB ====================
reports_container = tb.Frame(reports_tab)
reports_container.pack(fill='both', expand=True, padx=20, pady=20)

# Reports Header
rep_header = tb.Label(reports_container, 
                     text="📈 Reports & Analytics",
                     font=("Helvetica", 20, "bold"),
                     bootstyle="inverse-primary")
rep_header.pack(pady=(0, 20))

# Report Cards
report_cards_frame = tb.Frame(reports_container)
report_cards_frame.pack(fill='x', pady=(0, 20))

def create_report_card(parent, title, description, command, color):
    card = tb.Labelframe(parent, text=title, padding=20, bootstyle=color)
    card.pack(side='left', fill='both', expand=True, padx=10)
    
    tb.Label(card, text=description, 
             font=("Helvetica", 10), 
             wraplength=200).pack(pady=(0, 15))
    
    tb.Button(card, text="Generate Report",
             command=command,
             bootstyle=f"{color}").pack()

create_report_card(report_cards_frame, "📅 Monthly Report",
                  "View attendance statistics for the current month",
                  generate_monthly_report, "success")

create_report_card(report_cards_frame, "⚠️ Expiring Courses",
                  "Students whose courses are ending soon",
                  view_expiring_courses, "warning")

create_report_card(report_cards_frame, "💰 Financial Report",
                  "View fees collection and pending payments",
                  lambda: generate_financial_report(), "info")

def generate_financial_report():
    report_window = tb.Toplevel(root)
    report_window.title("Financial Report")
    report_window.geometry("900x700")
    
    main_frame = tb.Frame(report_window, padding=20)
    main_frame.pack(fill='both', expand=True)
    
    tb.Label(main_frame, text="💰 Financial Report", 
             font=("Helvetica", 18, "bold"),
             bootstyle="inverse-info").pack(pady=(0, 20))
    
    # Summary statistics
    summary_frame = tb.Frame(main_frame)
    summary_frame.pack(fill='x', pady=(0, 20))
    
    cursor.execute("SELECT SUM(total_fees), SUM(fees_paid), SUM(total_fees - fees_paid) FROM students")
    total, paid, pending = cursor.fetchone()
    
    stats = [
        ("Total Fees", f"₹{float(total or 0):,.2f}", "info"),
        ("Collected", f"₹{float(paid or 0):,.2f}", "success"),
        ("Pending", f"₹{float(pending or 0):,.2f}", "danger")
    ]
    
    for label, value, color in stats:
        card = tb.Frame(summary_frame, bootstyle=color)
        card.pack(side='left', fill='both', expand=True, padx=10)
        tb.Label(card, text=label, font=("Helvetica", 10), 
                bootstyle=color).pack(pady=5)
        tb.Label(card, text=value, font=("Helvetica", 16, "bold"),
                bootstyle=color).pack(pady=5)
    
    # Detailed list
    detail_frame = tb.Labelframe(main_frame, text="Student Fees Details", padding=15)
    detail_frame.pack(fill='both', expand=True)
    
    tree = ttk.Treeview(detail_frame, 
                       columns=("Roll No", "Name", "Total", "Paid", "Pending", "Status"),
                       show='headings', height=20)
    
    for col in ("Roll No", "Name", "Total", "Paid", "Pending", "Status"):
        tree.heading(col, text=col)
        tree.column(col, width=120)
    
    cursor.execute("SELECT roll_no, name, total_fees, fees_paid FROM students")
    for roll, name, total, paid in cursor.fetchall():
        pending = float(total) - float(paid)
        status = "✓ Paid" if pending <= 0 else "⚠ Pending"
        tree.insert("", "end", values=(
            roll, name, 
            f"₹{float(total):,.2f}", 
            f"₹{float(paid):,.2f}",
            f"₹{pending:,.2f}",
            status
        ))
    
    tree.pack(fill='both', expand=True)

# ==================== FEES TAB ====================
fees_container = tb.Frame(fees_tab)
fees_container.pack(fill='both', expand=True, padx=20, pady=20)

# Fees Header
fees_header = tb.Label(fees_container, 
                      text="💰 Fees Management",
                      font=("Helvetica", 20, "bold"),
                      bootstyle="inverse-warning")
fees_header.pack(pady=(0, 20))

# Fees summary cards
fees_summary_frame = tb.Frame(fees_container)
fees_summary_frame.pack(fill='x', pady=(0, 20))

cursor.execute("SELECT SUM(total_fees), SUM(fees_paid), COUNT(*) FROM students WHERE total_fees > fees_paid")
total_pending_fees, total_paid, pending_count = cursor.fetchone()
pending_amount = (float(total_pending_fees or 0) - float(total_paid or 0))

fees_stats = [
    ("Students with Pending Fees", str(pending_count or 0), "warning"),
    ("Total Pending Amount", f"₹{pending_amount:,.2f}", "danger"),
    ("Collection Rate", f"{(float(total_paid or 0) / float(total_pending_fees or 1) * 100):.1f}%", "success")
]

for label, value, color in fees_stats:
    card = tb.Frame(fees_summary_frame, bootstyle=color)
    card.pack(side='left', fill='both', expand=True, padx=10)
    inner = tb.Frame(card, bootstyle=color)
    inner.pack(fill='both', expand=True, padx=15, pady=15)
    tb.Label(inner, text=value, font=("Helvetica", 24, "bold"),
            bootstyle=color).pack()
    tb.Label(inner, text=label, font=("Helvetica", 11),
            bootstyle=color).pack()

# Pending fees list
pending_frame = tb.Labelframe(fees_container, text="Students with Pending Fees", 
                             padding=20, bootstyle="warning")
pending_frame.pack(fill='both', expand=True)

pending_tree = ttk.Treeview(pending_frame,
                           columns=("Roll No", "Name", "Total Fees", "Paid", "Pending", "Action"),
                           show='headings', height=15)

for col in ("Roll No", "Name", "Total Fees", "Paid", "Pending", "Action"):
    pending_tree.heading(col, text=col)
    pending_tree.column(col, width=130)

cursor.execute("""
    SELECT roll_no, name, total_fees, fees_paid 
    FROM students 
    WHERE total_fees > fees_paid
    ORDER BY (total_fees - fees_paid) DESC
""")

for roll, name, total, paid in cursor.fetchall():
    pending = float(total) - float(paid)
    pending_tree.insert("", "end", values=(
        roll, name,
        f"₹{float(total):,.2f}",
        f"₹{float(paid):,.2f}",
        f"₹{pending:,.2f}",
        "Click to Pay"
    ))

pending_tree.pack(fill='both', expand=True)

def on_fees_double_click(event):
    selection = pending_tree.selection()
    if selection:
        item = pending_tree.item(selection[0])
        roll_no = item['values'][0]
        # Simulate selecting the student and opening fees details
        show_fees_details_direct(roll_no)

def show_fees_details_direct(roll_no):
    cursor.execute("""
        SELECT name, email, total_fees, fees_paid, course_end_date 
        FROM students 
        WHERE roll_no = ?
    """, (roll_no,))
    
    student_data = cursor.fetchone()
    if not student_data:
        messagebox.showerror("Error", "Student not found!")
        return
    
    student_name, email, total_fees, fees_paid, course_end_date = student_data
    show_fees_details()

pending_tree.bind("<Double-1>", on_fees_double_click)

# Initialize the view
view_students()

root.mainloop() 