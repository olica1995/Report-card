import sys
import sqlite3
from PyQt5.QtWidgets import *
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- DATABASE ----------------
conn = sqlite3.connect("school.db")
cur = conn.cursor()


def init_db():
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT,
        password TEXT,
        role TEXT,
        class TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        subject TEXT,
        score REAL,
        term TEXT,
        year TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        amount REAL,
        status TEXT
    )""")

    conn.commit()


# ---------------- AUTH ----------------

def login(user_id, password):
    cur.execute("SELECT * FROM users WHERE id=? AND password=?", (user_id, password))
    user = cur.fetchone()
    if user:
        return {"id": user[0], "name": user[1], "role": user[3], "class": user[4]}
    return None


# ---------------- REPORT GENERATION ----------------

def generate_report(student_id):
    cur.execute("SELECT subject, score FROM marks WHERE student_id=?", (student_id,))
    marks = cur.fetchall()

    if not marks:
        QMessageBox.warning(None, "Error", "No marks found")
        return

    cur.execute("SELECT name, class FROM users WHERE id=?", (student_id,))
    user = cur.fetchone()
    student_name = user[0] if user else "Unknown"
    student_class = user[1] if user else "Unknown"

    # Rank
    cur.execute("""
    SELECT student_id, AVG(score) as avg_score
    FROM marks
    GROUP BY student_id
    ORDER BY avg_score DESC
    """)

    rankings = cur.fetchall()
    rank = 1
    for r in rankings:
        if r[0] == student_id:
            break
        rank += 1

    def get_grade(score):
        if score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    doc = SimpleDocTemplate(f"{student_id}_report.pdf")
    styles = getSampleStyleSheet()
    content = []

    # Header
    content.append(Paragraph("<b>GREENFIELD SECONDARY SCHOOL</b>", styles["Title"]))
    content.append(Paragraph("STUDENT REPORT CARD", styles["Heading2"]))
    content.append(Spacer(1, 15))

    # Student Info
    info = [
        ["Student ID:", student_id],
        ["Name:", student_name],
        ["Class:", student_class],
        ["Class Rank:", str(rank)]
    ]

    info_table = Table(info)
    info_table.setStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold")
    ])

    content.append(info_table)
    content.append(Spacer(1, 20))

    # Marks Table
    table_data = [["Subject", "Score", "Grade"]]
    total = 0

    for subject, score in marks:
        grade = get_grade(score)
        table_data.append([subject, score, grade])
        total += score

    avg = total / len(marks)

    table_data.append(["Total", total, ""])
    table_data.append(["Average", round(avg, 2), ""])

    marks_table = Table(table_data)
    marks_table.setStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ])

    content.append(marks_table)
    content.append(Spacer(1, 20))

    # Remarks
    if avg >= 75:
        remark = "Excellent performance. Keep it up."
    elif avg >= 50:
        remark = "Good performance. Work harder."
    else:
        remark = "Needs improvement. Focus on studies."

    content.append(Paragraph(f"<b>Remarks:</b> {remark}", styles["Normal"]))
    content.append(Spacer(1, 30))

    # Signature
    sig = Table([
        ["Class Teacher Signature", "Head Teacher Signature"],
        ["____________________", "____________________"]
    ])

    content.append(sig)

    doc.build(content)
    QMessageBox.information(None, "Success", f"{student_id}_report.pdf generated")


# ---------------- PANELS ----------------

class AdminPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.id = QLineEdit()
        self.id.setPlaceholderText("User ID")

        self.name = QLineEdit()
        self.name.setPlaceholderText("Name")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")

        self.role = QComboBox()
        self.role.addItems(["admin", "teacher", "learner", "bursar"])

        self.class_field = QLineEdit()
        self.class_field.setPlaceholderText("Class")

        btn = QPushButton("Create User")
        btn.clicked.connect(self.create_user)

        layout.addWidget(self.id)
        layout.addWidget(self.name)
        layout.addWidget(self.password)
        layout.addWidget(self.role)
        layout.addWidget(self.class_field)
        layout.addWidget(btn)

        self.setLayout(layout)

    def create_user(self):
        cur.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                    (self.id.text(), self.name.text(),
                     self.password.text(),
                     self.role.currentText(),
                     self.class_field.text()))
        conn.commit()
        QMessageBox.information(self, "Success", "User created")


class TeacherPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.sid = QLineEdit()
        self.sid.setPlaceholderText("Student ID")

        self.subject = QLineEdit()
        self.subject.setPlaceholderText("Subject")

        self.score = QLineEdit()
        self.score.setPlaceholderText("Score")

        self.term = QLineEdit()
        self.term.setPlaceholderText("Term")

        self.year = QLineEdit()
        self.year.setPlaceholderText("Year")

        btn = QPushButton("Save Marks")
        btn.clicked.connect(self.save)

        layout.addWidget(self.sid)
        layout.addWidget(self.subject)
        layout.addWidget(self.score)
        layout.addWidget(self.term)
        layout.addWidget(self.year)
        layout.addWidget(btn)

        self.setLayout(layout)

    def save(self):
        cur.execute("INSERT INTO marks (student_id, subject, score, term, year) VALUES (?,?,?,?,?)",
                    (self.sid.text(), self.subject.text(), float(self.score.text()), self.term.text(), self.year.text()))
        conn.commit()
        QMessageBox.information(self, "Saved", "Marks recorded")


class LearnerPanel(QWidget):
    def __init__(self, student_id):
        super().__init__()
        layout = QVBoxLayout()

        btn = QPushButton("Download Report")
        btn.clicked.connect(lambda: generate_report(student_id))

        layout.addWidget(btn)
        self.setLayout(layout)


class BursarPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.sid = QLineEdit()
        self.sid.setPlaceholderText("Student ID")

        self.amount = QLineEdit()
        self.amount.setPlaceholderText("Amount")

        self.status = QComboBox()
        self.status.addItems(["Paid", "Pending"])

        btn = QPushButton("Record Fee")
        btn.clicked.connect(self.save)

        layout.addWidget(self.sid)
        layout.addWidget(self.amount)
        layout.addWidget(self.status)
        layout.addWidget(btn)

        self.setLayout(layout)

    def save(self):
        cur.execute("INSERT INTO fees (student_id, amount, status) VALUES (?,?,?)",
                    (self.sid.text(), float(self.amount.text()), self.status.currentText()))
        conn.commit()
        QMessageBox.information(self, "Saved", "Fee recorded")


class Dashboard(QWidget):
    def __init__(self, user):
        super().__init__()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"Welcome {user['name']} ({user['role']})"))

        if user["role"] == "admin":
            layout.addWidget(AdminPanel())
        elif user["role"] == "teacher":
            layout.addWidget(TeacherPanel())
        elif user["role"] == "learner":
            layout.addWidget(LearnerPanel(user["id"]))
        elif user["role"] == "bursar":
            layout.addWidget(BursarPanel())

        self.setLayout(layout)


class Login(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success

        layout = QVBoxLayout()

        self.id = QLineEdit()
        self.id.setPlaceholderText("User ID")

        self.pw = QLineEdit()
        self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QLineEdit.Password)

        btn = QPushButton("Login")
        btn.clicked.connect(self.handle)

        layout.addWidget(self.id)
        layout.addWidget(self.pw)
        layout.addWidget(btn)

        self.setLayout(layout)

    def handle(self):
        user = login(self.id.text(), self.pw.text())
        if user:
            self.on_success(user)
        else:
            QMessageBox.warning(self, "Error", "Invalid login")


class App(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.login = Login(self.open_dashboard)
        self.addWidget(self.login)

    def open_dashboard(self, user):
        self.dashboard = Dashboard(user)
        self.addWidget(self.dashboard)
        self.setCurrentWidget(self.dashboard)


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()

    app = QApplication(sys.argv)
    window = App()
    window.setWindowTitle("School ERP System")
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec_())
