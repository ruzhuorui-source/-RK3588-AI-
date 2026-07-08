import sys
import serial
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QDesktopWidget,
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QDialog)
from PyQt5.QtGui import QFont, QKeyEvent
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import cv2
import time
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap
from rknnpool.rknnpool_ld import rknnPoolExecutor
from func.func_yolov8_optimize import myFunc

# ====================== 全局共享数据 ======================
global_express_data = [
    {"code": "A01-001", "position": "A区1号货架-01格口"},
    {"code": "A01-002", "position": "A区1号货架-02格口"},
    {"code": "B02-005", "position": "B区2号货架-05格口"},
    {"code": "B02-008", "position": "B区2号货架-08格口"},
    {"code": "C03-010", "position": "C区3号货架-10格口"},
    {"code": "C03-015", "position": "C区3号货架-15格口"},
    {"code": "D04-020", "position": "D区4号货架-20格口"},
]
global_patrol_status = "空闲中"
global_safety_level = "低"
global_safety_alert_count = 0
FONT_FAMILY = '"Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif'

# 串口全局存储变量
global_fire_alarm = 0
global_m1 = 0
global_m2 = 0
global_m3 = 0
global_m4 = 0

# 串口线程全局对象
serial_thread = None

# ====================== 全局全屏适配工具函数 ======================
def fit_screen_and_fullscreen(window):
    screen_rect = QDesktopWidget().availableGeometry()
    window.setGeometry(screen_rect)
    window.showFullScreen()

# ====================== 串口后台线程（不阻塞UI） ======================
class SerialThread(QThread):
    sig_alarm = pyqtSignal()  # 触发环境异常弹窗信号
    def __init__(self):
        super().__init__()
        self.ser = None
        self.running = True

    # 新增对外发送串口数据接口
    def send_msg(self, data: bytes):
        if self.ser and self.ser.is_open:
            self.ser.write(data)

    def run(self):
        try:
            self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.5)
            print("串口打开成功，开始监听")
            self.ser.write(b'Hello from Python UART9!\n')
        except Exception as e:
            print("串口打开失败:", e)
            return

        while self.running:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                recv_str = data.decode('utf-8', errors='replace').strip()
                lines = recv_str.splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) != 5:
                        continue
                    try:
                        fire_alarm = int(parts[0])
                        m1 = int(parts[1])
                        m2 = int(parts[2])
                        m3 = int(parts[3])
                        m4 = int(parts[4])
                        # 更新全局变量
                        global global_fire_alarm, global_m1, global_m2, global_m3, global_m4
                        global_fire_alarm = fire_alarm
                        global_m1 = m1
                        global_m2 = m2
                        global_m3 = m3
                        global_m4 = m4
                        print(f"报警:{fire_alarm} M1:{m1} M2:{m2} M3:{m3} M4:{m4}")
                        # 报警标志为1，发送信号弹出弹窗
                        if fire_alarm == 1:
                            self.sig_alarm.emit()
                    except ValueError:
                        continue
            time.sleep(0.1)
        if self.ser.is_open:
            self.ser.close()

    def stop(self):
        self.running = False
        self.wait()

# ====================== 自定义故障弹窗 ======================
class FaultAlertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 220)
        self.init_ui()
        if parent:
            self.move(parent.x() + (parent.width() - self.width()) // 2,
                      parent.y() + (parent.height() - self.height()) // 2)

    def init_ui(self):
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background:#fff;
                border-radius:12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        """)

        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(30, 25, 30, 25)
        main_lay.setSpacing(18)

        title_lay = QHBoxLayout()
        title_lay.setSpacing(12)
        icon_label = QLabel("⚠")
        icon_label.setStyleSheet("font-size:32px; color:#f56c6c;")
        title_text = QLabel("设备故障警告")
        title_text.setStyleSheet(f"font-size:22px; font-weight:bold; color:#c23939; font-family:{FONT_FAMILY};")
        title_lay.addWidget(icon_label)
        title_lay.addWidget(title_text)
        title_lay.addStretch(1)

        content = QLabel("巡逻故障，请及时检查设备！")
        content.setStyleSheet(f"font-size:16px; color:#303133; font-family:{FONT_FAMILY};")
        content.setAlignment(Qt.AlignCenter)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch(1)
        confirm_btn = QPushButton("我知道了")
        confirm_btn.setFixedSize(140, 42)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f78989, stop:1 #f56c6c);
                color:#fff; border:none; border-radius:8px;
                font-size:16px; font-weight:bold; font-family:{FONT_FAMILY};
                border-top:1px solid rgba(255,255,255,0.3);
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f9a0a0, stop:1 #f78989); }}
        """)
        confirm_btn.clicked.connect(self.accept)
        btn_lay.addWidget(confirm_btn)
        btn_lay.addStretch(1)

        main_lay.addLayout(title_lay)
        main_lay.addWidget(content)
        main_lay.addLayout(btn_lay)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(container)

# ====================== 自定义环境异常弹窗 ======================
class SafetyAlertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 220)
        self.init_ui()
        if parent:
            self.move(parent.x() + (parent.width() - self.width()) // 2,
                      parent.y() + (parent.height() - self.height()) // 2)

    def init_ui(self):
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background:#fff;
                border-radius:12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        """)

        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(30, 25, 30, 25)
        main_lay.setSpacing(18)

        title_lay = QHBoxLayout()
        title_lay.setSpacing(12)
        icon_label = QLabel("⚠")
        icon_label.setStyleSheet("font-size:32px; color:#e6a23c;")
        title_text = QLabel("环境异常警告")
        title_text.setStyleSheet(f"font-size:22px; font-weight:bold; color:#cf8300; font-family:{FONT_FAMILY};")
        title_lay.addWidget(icon_label)
        title_lay.addWidget(title_text)
        title_lay.addStretch(1)

        content = QLabel("当前环境安全等级过高，请及时检查环境！")
        content.setStyleSheet(f"font-size:16px; color:#303133; font-family:{FONT_FAMILY};")
        content.setAlignment(Qt.AlignCenter)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch(1)
        confirm_btn = QPushButton("我知道了")
        confirm_btn.setFixedSize(140, 42)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ebb563, stop:1 #e6a23c);
                color:#fff; border:none; border-radius:8px;
                font-size:16px; font-weight:bold; font-family:{FONT_FAMILY};
                border-top:1px solid rgba(255,255,255,0.3);
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0c680, stop:1 #ebb563); }}
        """)
        confirm_btn.clicked.connect(self.accept)
        btn_lay.addWidget(confirm_btn)
        btn_lay.addStretch(1)

        main_lay.addLayout(title_lay)
        main_lay.addWidget(content)
        main_lay.addLayout(btn_lay)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(container)

# ====================== 自定义电机状态弹窗（支持动态传参） ======================
class MotorStatusDialog(QDialog):
    def __init__(self, m1,m2,m3,m4, parent=None):
        super().__init__(parent)
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3
        self.m4 = m4
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 220)
        self.init_ui()
        if parent:
            self.move(parent.x() + (parent.width() - self.width()) // 2,
                      parent.y() + (parent.height() - self.height()) // 2)

    def init_ui(self):
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background:#fff;
                border-radius:12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        """)

        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(30, 25, 30, 25)
        main_lay.setSpacing(18)

        title_lay = QHBoxLayout()
        title_lay.setSpacing(12)
        icon_label = QLabel("⚙")
        icon_label.setStyleSheet("font-size:32px; color:#409eff;")
        title_text = QLabel("电机运行状态")
        title_text.setStyleSheet(f"font-size:22px; font-weight:bold; color:#0066cc; font-family:{FONT_FAMILY};")
        title_lay.addWidget(icon_label)
        title_lay.addWidget(title_text)
        title_lay.addStretch(1)

        # 横向展示电机数据
        content = QLabel(f"M1:{self.m1}    M2:{self.m2}    M3:{self.m3}    M4:{self.m4}")
        content.setStyleSheet(f"font-size:16px; color:#303133; font-family:{FONT_FAMILY};")
        content.setAlignment(Qt.AlignCenter)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch(1)
        confirm_btn = QPushButton("我知道了")
        confirm_btn.setFixedSize(140, 42)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66b1ff, stop:1 #409eff);
                color:#fff; border:none; border-radius:8px;
                font-size:16px; font-weight:bold; font-family:{FONT_FAMILY};
                border-top:1px solid rgba(255,255,255,0.3);
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #80c0ff, stop:1 #66b1ff); }}
        """)
        confirm_btn.clicked.connect(self.accept)
        btn_lay.addWidget(confirm_btn)
        btn_lay.addStretch(1)

        main_lay.addLayout(title_lay)
        main_lay.addWidget(content)
        main_lay.addLayout(btn_lay)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(container)

# ====================== 通用虚拟键盘组件（缩小按键高度） ======================
class KeyBoardWidget(QWidget):
    def __init__(self, target_input, confirm_callback=None):
        super().__init__()
        self.target_input = target_input
        self.confirm_callback = confirm_callback
        self.init_ui()
        self.setStyleSheet(f"""
            QPushButton#keyBtn {{
                min-width:60px; min-height:42px; font-size:16px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f7fa);
                color:#303133; border:1px solid #ddd; border-radius:6px;
                font-family: {FONT_FAMILY};
                border-top:1px solid #fff;
            }}
            QPushButton#keyBtn:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0f7ff, stop:1 #ecf5ff);}}
            QPushButton#keyDel{{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff0f0, stop:1 #ffeeee);
                color:#c00; border:1px solid #ffcccc;
            }}
            QPushButton#keyEnter{{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #33bb66, stop:1 #009944);
                color:#fff; border:1px solid #008833;
                border-top:1px solid #66dd88;
            }}
        """)

    def init_ui(self):
        layout = QGridLayout()
        layout.setSpacing(4)  # 键盘格子间距缩小
        keys = [
            ["1", "2", "3", "退格"],
            ["4", "5", "6", "清空"],
            ["7", "8", "9", "确认"],
            ["0", "-", "A", "B"]
        ]
        for row_idx, row in enumerate(keys):
            for col_idx, txt in enumerate(row):
                btn = QPushButton(txt)
                if txt in ["退格", "清空"]:
                    btn.setObjectName("keyDel")
                elif txt == "确认":
                    btn.setObjectName("keyEnter")
                else:
                    btn.setObjectName("keyBtn")
                btn.clicked.connect(lambda checked, t=txt: self.on_key_click(t))
                layout.addWidget(btn, row_idx, col_idx)
        self.setLayout(layout)

    def on_key_click(self, text):
        if text == "退格":
            self.target_input.backspace()
        elif text == "清空":
            self.target_input.clear()
        elif text == "确认":
            if self.confirm_callback is not None:
                self.confirm_callback()
        else:
            self.target_input.insert(text)

# ====================== 基础窗口类（和查询界面完全一致，无额外Flags） ======================
class BaseWindow(QWidget):
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.close()
        else:
            super().keyPressEvent(event)

# ====================== 首页主菜单 ======================
class HomeWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快递管理系统-首页")
        self.init_style()
        self.init_ui()
        self.refresh_safety_status()
        self.refresh_patrol_status()

    # 串口信号绑定：收到报警信号弹出环境弹窗
    def show_safety_alert_from_serial(self):
        dialog = SafetyAlertDialog(self)
        dialog.exec_()

    def init_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f0fe, stop:1 #f5f7fa);
                font-family: {FONT_FAMILY};
                font-size:16px;
            }}
            #mainCard {{
                background-color: #ffffff;
                border-radius: 16px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
            }}
            QPushButton{{
                width:280px; height:90px; font-size:22px; font-weight:bold;
                border:none; border-radius:12px; color:white;
                border-top: 1px solid rgba(255,255,255,0.3);
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }}
            #btnQuery{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66b1ff, stop:1 #409eff);}}
            #btnQuery:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #80c0ff, stop:1 #66b1ff);}}
            #btnAdd{{background: qlineargradient(x1:0, y1:0, x2:0, stop:0 #85ce61, stop:1 #67c23a);}}
            #btnAdd:hover{{background: qlineargradient(x1:0, y1:0, x2:0, stop:0 #9fd87f, stop:1 #85ce61);}}
            #btnPatrol{{background: qlineargradient(x1:0, y1:0, x2:0, stop:0 #ebb563, stop:1 #e6a23c);}}
            #btnPatrol:hover{{background: qlineargradient(x1:0, y1:0, x2:0, stop:0 #f0c680, stop:1 #ebb563);}}
            #btnFault{{
                width:130px; height:40px; font-size:13px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dd5151, stop:1 #c23939);
            }}
            #btnFault:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e86b6b, stop:1 #dd5151);}}
            #btnSafetySwitch{{
                width:110px; height:40px; font-size:13px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a6a9ad, stop:1 #909399);
            }}
            #btnSafetySwitch:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #bdc0c4, stop:1 #a6a9ad);}}
            .status-tag {{
                font-size:16px; font-weight:bold; padding:6px 12px;
                border-radius:8px;
            }}
        """)

    def init_ui(self):
        main_lay = QVBoxLayout()
        main_lay.setContentsMargins(20, 15, 20, 10)
        main_lay.setSpacing(15)

        # 顶部状态栏
        status_lay = QHBoxLayout()
        status_lay.setSpacing(15)

        # 巡逻状态：指示灯+文字
        patrol_lay = QHBoxLayout()
        patrol_lay.setSpacing(6)
        self.patrol_dot = QLabel()
        self.patrol_dot.setFixedSize(12,12)
        self.patrol_status_label = QLabel("巡逻状态：空闲中")
        self.patrol_status_label.setProperty("class", "status-tag")
        patrol_lay.addWidget(self.patrol_dot)
        patrol_lay.addWidget(self.patrol_status_label)

        # 安全等级：指示灯+文字
        safety_lay = QHBoxLayout()
        safety_lay.setSpacing(6)
        self.safety_dot = QLabel()
        self.safety_dot.setFixedSize(12,12)
        self.safety_label = QLabel("安全等级：低")
        self.safety_label.setProperty("class", "status-tag")
        safety_lay.addWidget(self.safety_dot)
        safety_lay.addWidget(self.safety_label)

        self.btn_safety_switch = QPushButton("切换安全等级")
        self.btn_safety_switch.setObjectName("btnSafetySwitch")
        self.btn_sim_fault = QPushButton("模拟巡逻故障")
        self.btn_sim_fault.setObjectName("btnFault")
        # 新增电机情况按钮
        self.btn_motor = QPushButton("电机情况")
        self.btn_motor.setObjectName("btnSafetySwitch")

        status_lay.addLayout(patrol_lay)
        status_lay.addLayout(safety_lay)
        status_lay.addStretch(1)
        status_lay.addWidget(self.btn_safety_switch)
        status_lay.addWidget(self.btn_sim_fault)
        status_lay.addWidget(self.btn_motor)

        # 白色主卡片（收紧内边距）
        card = QWidget()
        card.setObjectName("mainCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(40, 25, 40, 25)
        card_lay.setSpacing(20)

        # 带装饰线标题
        title_lay = QHBoxLayout()
        title_lay.setSpacing(15)
        line1 = QLabel()
        line1.setFixedHeight(2)
        line1.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:1 #409eff);")
        title = QLabel("快递仓储管理系统")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:28px; font-weight:700; color:#1f2d3d; background:transparent;")
        line2 = QLabel()
        line2.setFixedHeight(2)
        line2.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #409eff, stop:1 transparent);")
        title_lay.addWidget(line1, 1)
        title_lay.addWidget(title)
        title_lay.addWidget(line2, 1)

        self.btn_query = QPushButton("查询快递")
        self.btn_query.setObjectName("btnQuery")
        self.btn_add = QPushButton("录入快递")
        self.btn_add.setObjectName("btnAdd")
        self.btn_patrol = QPushButton("巡逻")
        self.btn_patrol.setObjectName("btnPatrol")

        card_lay.addLayout(title_lay)
        card_lay.addWidget(self.btn_query, alignment=Qt.AlignCenter)
        card_lay.addWidget(self.btn_add, alignment=Qt.AlignCenter)
        card_lay.addWidget(self.btn_patrol, alignment=Qt.AlignCenter)

        main_lay.addLayout(status_lay)
        main_lay.addStretch(1)
        main_lay.addWidget(card, alignment=Qt.AlignCenter)
        main_lay.addStretch(1)
        self.setLayout(main_lay)

        self.btn_sim_fault.clicked.connect(self.trigger_fault_alert)
        self.btn_safety_switch.clicked.connect(self.switch_safety_level)
        self.btn_motor.clicked.connect(self.show_motor_info)

    # 读取全局串口电机数据，动态弹窗
    def show_motor_info(self):
        global global_m1, global_m2, global_m3, global_m4
        dialog = MotorStatusDialog(global_m1, global_m2, global_m3, global_m4, self)
        dialog.exec_()

    def refresh_patrol_status(self):
        self.patrol_status_label.setText(f"巡逻状态：{global_patrol_status}")
        if global_patrol_status == "空闲中":
            self.patrol_dot.setStyleSheet("background-color:#67c23a; border-radius:6px;")
            self.patrol_status_label.setStyleSheet("""
                font-size:16px; font-weight:bold; padding:6px 12px;
                background-color:#f0f9eb; border-radius:8px; color:#67c23a;
            """)
        else:
            self.patrol_dot.setStyleSheet("background-color:#409eff; border-radius:6px;")
            self.patrol_status_label.setStyleSheet("""
                font-size:16px; font-weight:bold; padding:6px 12px;
                background-color:#e6f0ff; border-radius:8px; color:#0066cc;
            """)

    def refresh_safety_status(self):
        self.safety_label.setText(f"安全等级：{global_safety_level}")
        if global_safety_level == "低":
            self.safety_dot.setStyleSheet("background-color:#67c23a; border-radius:6px;")
            self.safety_label.setStyleSheet("""
                font-size:16px; font-weight:bold; padding:6px 12px;
                background-color:#f0f9eb; border-radius:8px; color:#67c23a;
            """)
        elif global_safety_level == "中":
            self.safety_dot.setStyleSheet("background-color:#e6a23c; border-radius:6px;")
            self.safety_label.setStyleSheet("""
                font-size:16px; font-weight:bold; padding:6px 12px;
                background-color:#fdf6ec; border-radius:8px; color:#e6a23c;
            """)
        else:
            self.safety_dot.setStyleSheet("background-color:#f56c6c; border-radius:6px;")
            self.safety_label.setStyleSheet("""
                font-size:16px; font-weight:bold; padding:6px 12px;
                background-color:#fef0f0; border-radius:8px; color:#f56c6c;
            """)

    def trigger_fault_alert(self):
        global global_patrol_status
        dialog = FaultAlertDialog(self)
        dialog.exec_()
        global_patrol_status = "空闲中"
        self.refresh_patrol_status()

    def switch_safety_level(self):
        global global_safety_level, global_safety_alert_count
        level_order = ["低", "中", "高"]
        current_idx = level_order.index(global_safety_level)
        next_idx = (current_idx + 1) % 3
        global_safety_level = level_order[next_idx]
        self.refresh_safety_status()

        if global_safety_level == "高":
            if global_safety_alert_count < 3:
                dialog = SafetyAlertDialog(self)
                dialog.exec_()
                global_safety_alert_count += 1
        else:
            global_safety_alert_count = 0


# ====================== 图像推理子线程 ======================
class DetectThread(QThread):
    # 信号：传回推理画面、打印FPS日志
    sig_frame = pyqtSignal(QPixmap)
    sig_fps = pyqtSignal(str)
    sig_exit = pyqtSignal()

    # YOLO全局配置（和你独立脚本保持一致）
    modelPath = "./box.rknn"
    video_source = "/dev/video11"
    TPEs = 8
    save_video = True
    output_video_path = "output_video.mp4"
    max_display_w = 1280
    max_display_h = 800

    def __init__(self):
        super().__init__()
        self._stop = False
        self.pool = None
        self.cap = None
        self.writer = None

    def stop_task(self):
        self._stop = True

    def run(self):
        # 初始化RKNN池
        self.pool = rknnPoolExecutor(rknnModel=self.modelPath, TPEs=self.TPEs, func=myFunc)
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            print(f"摄像头 {self.video_source} 打开失败")
            self.sig_exit.emit()
            self.pool.release()
            return

        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            width, height = 640, 640

        # 视频保存
        if self.save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(self.output_video_path, fourcc, fps, (width, height))

        frames = 0
        loop_time = time.time()
        while self.cap.isOpened() and not self._stop:
            ret, frame = self.cap.read()
            if not ret:
                break
            self.pool.put(frame)
            result_frame, flag = self.pool.get()
            if not flag:
                break

            frames += 1
            # 写入视频
            if self.writer:
                self.writer.write(result_frame)

            # 缩放适配窗口
            h_img, w_img = result_frame.shape[:2]
            scale = min(self.max_display_w / w_img, self.max_display_h / h_img)
            dw, dh = int(w_img * scale), int(h_img * scale)
            display = cv2.resize(result_frame, (dw, dh))

            # OpenCV BGR 转 Qt RGB
            rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            self.sig_frame.emit(pix)

            # 每30帧输出FPS
            if frames % 30 == 0:
                cost = time.time() - loop_time
                fps_text = f"近30帧FPS: {30 / cost:.2f}"
                self.sig_fps.emit(fps_text)
                loop_time = time.time()

        # 释放全部资源
        if self.writer:
            self.writer.release()
        self.cap.release()
        self.pool.release()
        self.sig_exit.emit()
        print("图像检测线程已退出，资源释放完成")

# ====================== 巡逻独立界面（改造后，集成YOLO检测） ======================
# ====================== 全屏检测窗口（带关闭按钮） ======================
class FullScreenDetectDialog(QDialog):
    def __init__(self, detect_thread, parent=None):
        super().__init__(parent)
        self.detect_thread = detect_thread
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("background:#000;")
        self.showFullScreen()
        self.init_ui()
        # 绑定检测线程信号
        self.detect_thread.sig_frame.connect(self.update_frame)
        self.detect_thread.sig_fps.connect(self.update_fps)
        self.detect_thread.sig_exit.connect(self.close)

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # 顶部工具栏：FPS + 关闭按钮
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("background:rgba(0,0,0,180);")
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(20, 0, 20, 0)

        self.lab_fps = QLabel("FPS: --")
        self.lab_fps.setStyleSheet("color:#f56c6c; font-size:18px; font-weight:bold;")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background:#f56c6c; color:#fff; border:none; 
                border-radius:18px; font-size:18px; font-weight:bold;
            }
            QPushButton:hover { background:#f78989; }
        """)
        self.btn_close.clicked.connect(self.close_detect)

        top_lay.addWidget(self.lab_fps)
        top_lay.addStretch(1)
        top_lay.addWidget(self.btn_close)

        # 画面显示区
        self.lab_frame = QLabel()
        self.lab_frame.setAlignment(Qt.AlignCenter)
        self.lab_frame.setStyleSheet("background:#000;")

        main_lay.addWidget(top_bar)
        main_lay.addWidget(self.lab_frame)

    def update_frame(self, pixmap):
        # 自适应全屏缩放
        scaled = pixmap.scaled(self.lab_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lab_frame.setPixmap(scaled)

    def update_fps(self, text):
        self.lab_fps.setText(text)

    def close_detect(self):
        if self.detect_thread and self.detect_thread.isRunning():
            self.detect_thread.stop_task()
            self.detect_thread.wait()
        self.accept()


# ====================== 巡逻独立界面（纯三按钮，无画面框） ======================
class PatrolWindow(BaseWindow):
    def __init__(self, home_win):
        super().__init__()
        self.home = home_win
        self.setWindowTitle("巡逻控制界面")
        self.init_style()
        self.init_ui()
        # 推理线程 + 全屏窗口
        self.detect_thread = None
        self.detect_dialog = None

    def showEvent(self, event):
        super().showEvent(event)
        self.stat_label.setText(f"当前状态：{global_patrol_status}")
        self.update_status_dot()

    def init_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f0fe, stop:1 #f5f7fa);
                font-family: {FONT_FAMILY};
                font-size:16px;
            }}
            #mainCard {{
                background-color: #ffffff;
                border-radius: 16px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
            }}
            QLabel#patrolStat{{
                font-size:20px; font-weight:bold; padding:10px 20px;
                background-color:#f0f7ff; border:2px solid #409eff; border-radius:10px;
                color:#0066cc;
            }}
            QPushButton{{
                width:260px; height:80px; font-size:20px; font-weight:bold;
                border:none; border-radius:10px; color:#fff;
                border-top: 1px solid rgba(255,255,255,0.3);
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }}
            #startBtn{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #85ce61, stop:1 #67c23a);}}
            #startBtn:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9fd87f, stop:1 #85ce61);}}
            #stopBtn{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f78989, stop:1 #f56c6c);}}
            #stopBtn:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f9a0a0, stop:1 #f78989);}}
            #backBtn{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a6a9ad, stop:1 #909399);}}
            #backBtn:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #bdc0c4, stop:1 #a6a9ad);}}
        """)

    def init_ui(self):
        main_lay = QVBoxLayout()
        main_lay.setContentsMargins(20, 15, 20, 10)
        main_lay.addStretch(1)

        card = QWidget()
        card.setObjectName("mainCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(40, 25, 40, 25)
        card_lay.setSpacing(22)

        title_lay = QHBoxLayout()
        title_lay.setSpacing(15)
        line1 = QLabel()
        line1.setFixedHeight(2)
        line1.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:1 #409eff);")
        title = QLabel("仓储巡逻控制")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:26px; font-weight:700; color:#1f2d3d; background:transparent;")
        line2 = QLabel()
        line2.setFixedHeight(2)
        line2.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #409eff, stop:1 transparent);")
        title_lay.addWidget(line1, 1)
        title_lay.addWidget(title)
        title_lay.addWidget(line2, 1)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.setAlignment(Qt.AlignCenter)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(14, 14)
        self.stat_label = QLabel(f"当前状态：{global_patrol_status}")
        self.stat_label.setObjectName("patrolStat")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.stat_label)

        self.btn_start = QPushButton("开始巡逻")
        self.btn_start.setObjectName("startBtn")
        self.btn_stop = QPushButton("停止巡逻")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_back = QPushButton("返回主界面")
        self.btn_back.setObjectName("backBtn")

        card_lay.addLayout(title_lay)
        card_lay.addLayout(status_row)
        card_lay.addWidget(self.btn_start, alignment=Qt.AlignCenter)
        card_lay.addWidget(self.btn_stop, alignment=Qt.AlignCenter)
        card_lay.addWidget(self.btn_back, alignment=Qt.AlignCenter)

        main_lay.addWidget(card, alignment=Qt.AlignCenter)
        main_lay.addStretch(1)
        self.setLayout(main_lay)

        self.btn_start.clicked.connect(self.start_patrol)
        self.btn_stop.clicked.connect(self.stop_patrol)
        self.btn_back.clicked.connect(self.back_home)

    def update_status_dot(self):
        if global_patrol_status == "空闲中":
            self.status_dot.setStyleSheet("background-color:#67c23a; border-radius:7px;")
        else:
            self.status_dot.setStyleSheet("background-color:#409eff; border-radius:7px;")

    def start_patrol(self):
        global global_patrol_status, serial_thread
        global_patrol_status = "正在巡逻"
        self.stat_label.setText(f"当前状态：{global_patrol_status}")
        self.update_status_dot()
        self.home.refresh_patrol_status()

        # 串口指令
        serial_thread.send_msg(b'F\r\n')
        QTimer.singleShot(50, lambda: serial_thread.send_msg(b'1\r\n'))

        # 启动YOLO检测线程 + 弹出全屏窗口
        if self.detect_thread is None or not self.detect_thread.isRunning():
            self.detect_thread = DetectThread()
            self.detect_dialog = FullScreenDetectDialog(self.detect_thread, self)
            self.detect_thread.start()
            self.detect_dialog.exec_()

    def stop_patrol(self):
        global global_patrol_status, serial_thread
        global_patrol_status = "空闲中"
        self.stat_label.setText(f"当前状态：{global_patrol_status}")
        self.update_status_dot()
        self.home.refresh_patrol_status()
        # 急停指令（只停小车，检测窗口继续开着）
        serial_thread.send_msg(b'S\r\n')

    def back_home(self):
        # 返回首页前强制关闭检测+释放资源
        if self.detect_thread and self.detect_thread.isRunning():
            self.detect_thread.stop_task()
            self.detect_thread.wait()
        if self.detect_dialog:
            self.detect_dialog.close()
        fit_screen_and_fullscreen(self.home)
        self.close()
# ====================== 查询快递界面 ======================
class QueryWindow(BaseWindow):
    def __init__(self, home_win):
        super().__init__()
        self.home = home_win
        self.setWindowTitle("快递查询")
        self.init_style()
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_all_data()

    def init_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f0fe, stop:1 #f5f7fa);
                font-family: {FONT_FAMILY};
                font-size: 14px; color: #303133;
            }}
            #tableCard, #keyboardCard {{
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
            }}
            QLabel#countLabel {{
                font-size: 18px; font-weight: bold; color: #0066cc;
                padding:6px 12px; background-color:#e6f0ff; border-radius:6px;
            }}
            QLineEdit {{
                background-color:#fff; border:1px solid #dcdfe6; border-radius:6px;
                padding:8px 12px; min-width:220px; font-size:16px;
                color:#303133;
            }}
            QLineEdit:focus {{ border-color:#409eff; outline:none; }}
            QPushButton {{
                color:white; border:none; border-radius:6px;
                padding:8px 18px; min-width:80px; font-size:15px;
                border-top: 1px solid rgba(255,255,255,0.3);
                border-bottom: 1px solid rgba(0,0,0,0.1);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66b1ff, stop:1 #409eff);
            }}
            QPushButton:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #80c0ff, stop:1 #66b1ff);}}
            QPushButton#resetBtn{{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f5f7fa);
                color:#606266; border:1px solid #ddd;
            }}
            QPushButton#resetBtn:hover{{color:#409eff; border-color:#c6e2ff; background:#ecf5ff;}}
            QPushButton#exitBtn{{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f78989, stop:1 #f56c6c);
            }}
            QPushButton#exitBtn:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f9a0a0, stop:1 #f78989);}}
            QTableWidget {{
                background-color:#fff; border:none; border-radius:8px;
                gridline-color:#f0f2f5; selection-background-color:#ecf5ff;
                font-size:14px;
            }}
            QHeaderView::section {{
                background-color:#fafafa; border:none; border-bottom:1px solid #ebeef5;
                padding:10px; font-weight:bold; color:#606266;
                font-size:15px;
            }}
        """)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 15, 20, 10)
        main_layout.setSpacing(12)

        table_card = QWidget()
        table_card.setObjectName("tableCard")
        table_lay = QVBoxLayout(table_card)
        table_lay.setContentsMargins(15, 15, 15, 15)
        table_lay.setSpacing(12)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        self.count_label = QLabel("快递总数：0")
        self.count_label.setObjectName("countLabel")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("下方键盘输入位置码")
        self.search_btn = QPushButton("查询")
        self.reset_btn = QPushButton("显示全部")
        self.reset_btn.setObjectName("resetBtn")
        self.back_btn = QPushButton("返回首页")
        self.exit_btn = QPushButton("退出程序")
        self.exit_btn.setObjectName("exitBtn")

        top_layout.addWidget(self.count_label)
        top_layout.addStretch(1)
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.search_btn)
        top_layout.addWidget(self.reset_btn)
        top_layout.addWidget(self.back_btn)
        top_layout.addWidget(self.exit_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["位置码", "存放位置"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)

        table_lay.addLayout(top_layout)
        table_lay.addWidget(self.table)

        keyboard_card = QWidget()
        keyboard_card.setObjectName("keyboardCard")
        keyboard_lay = QVBoxLayout(keyboard_card)
        keyboard_lay.setContentsMargins(15, 12, 15, 12)
        self.keyboard = KeyBoardWidget(self.search_input, self.query_express)
        keyboard_lay.addWidget(self.keyboard, alignment=Qt.AlignCenter)

        main_layout.addWidget(table_card)
        main_layout.addWidget(keyboard_card)
        self.setLayout(main_layout)

        self.search_btn.clicked.connect(self.query_express)
        self.reset_btn.clicked.connect(self.load_all_data)
        self.back_btn.clicked.connect(self.go_back_home)
        self.exit_btn.clicked.connect(self.close)
        self.search_input.returnPressed.connect(self.query_express)

    def go_back_home(self):
        fit_screen_and_fullscreen(self.home)
        self.close()

    def load_all_data(self):
        self.render_table(global_express_data)

    def query_express(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入位置码")
            return
        result = [item for item in global_express_data if keyword in item["code"]]
        self.render_table(result)
        if not result:
            QMessageBox.information(self, "查询结果", "未找到匹配的快递")

    def render_table(self, data_list):
        self.table.setRowCount(len(data_list))
        self.count_label.setText(f"快递总数：{len(data_list)}")
        for row, item in enumerate(data_list):
            code_item = QTableWidgetItem(item["code"])
            pos_item = QTableWidgetItem(item["position"])
            code_item.setTextAlignment(Qt.AlignCenter)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, code_item)
            self.table.setItem(row, 1, pos_item)

# ====================== 录入快递界面（终极压缩，解决底部裁切） ======================
class AddWindow(BaseWindow):
    def __init__(self, home_win):
        super().__init__()
        self.home = home_win
        self.setWindowTitle("录入新快递")
        self.init_style()
        self.init_ui()

    def init_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f0fe, stop:1 #f5f7fa);
                font-family: {FONT_FAMILY};
                font-size:16px;
            }}
            #mainCard {{
                background-color: #ffffff;
                border-radius: 16px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
            }}
            QLabel{{font-size:15px; font-weight:bold; color:#303133; background:transparent;}}
            QLineEdit{{
                background-color:#fff; border:1px solid #dcdfe6; border-radius:6px;
                padding:5px; font-size:16px; min-height:16px;
                color:#303133;
            }}
            QLineEdit:focus {{ border-color:#67c23a; outline:none; }}
            QPushButton{{
                border:none; border-radius:6px; padding:7px 16px; font-size:15px; color:white;
                border-top: 1px solid rgba(255,255,255,0.3);
                border-bottom: 1px solid rgba(0,0,0,0.1);
            }}
            #btnSave{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #85ce61, stop:1 #67c23a);}}
            #btnSave:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9fd87f, stop:1 #85ce61);}}
            #btnBack{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a6a9ad, stop:1 #909399);}}
            #btnBack:hover{{background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #bdc0c4, stop:1 #a6a9ad);}}
        """)

    def init_ui(self):
        # 外层布局大幅缩减上下边距
        main_lay = QVBoxLayout()
        main_lay.setContentsMargins(12, 6, 12, 4)
        main_lay.addStretch(1)

        card = QWidget()
        card.setObjectName("mainCard")
        card_lay = QVBoxLayout(card)
        # 卡片内部边距极致收紧
        card_lay.setContentsMargins(22, 12, 22, 10)
        card_lay.setSpacing(6)

        # 带装饰线标题
        title_lay = QHBoxLayout()
        title_lay.setSpacing(10)
        line1 = QLabel()
        line1.setFixedHeight(2)
        line1.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:1 #67c23a);")
        title = QLabel("录入快递信息")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:700; color:#1f2d3d; background:transparent;")
        line2 = QLabel()
        line2.setFixedHeight(2)
        line2.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #67c23a, stop:1 transparent);")
        title_lay.addWidget(line1, 1)
        title_lay.addWidget(title)
        title_lay.addWidget(line2, 1)

        code_lay = QHBoxLayout()
        code_lay.setSpacing(6)
        code_lay.addWidget(QLabel("位置码："))
        self.edit_code = QLineEdit()
        self.edit_code.setPlaceholderText("例：A01-003")
        code_lay.addWidget(self.edit_code)

        pos_lay = QHBoxLayout()
        pos_lay.setSpacing(6)
        pos_lay.addWidget(QLabel("存放位置："))
        self.edit_pos = QLineEdit()
        self.edit_pos.setPlaceholderText("例：A区1号货架-03格口")
        pos_lay.addWidget(self.edit_pos)

        self.keyboard = KeyBoardWidget(self.edit_code, self.save_data)
        tip_label = QLabel("* 虚拟键盘仅支持位置码输入，存放位置需外接键盘输入中文")
        tip_label.setStyleSheet("color:#909399; font-size:10px; font-weight:normal; background:transparent;")

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)
        self.btn_save = QPushButton("保存录入")
        self.btn_save.setObjectName("btnSave")
        self.btn_back = QPushButton("返回首页")
        self.btn_back.setObjectName("btnBack")
        btn_lay.addStretch(1)
        btn_lay.addWidget(self.btn_save)
        btn_lay.addWidget(self.btn_back)
        btn_lay.addStretch(1)

        card_lay.addLayout(title_lay)
        card_lay.addLayout(code_lay)
        card_lay.addLayout(pos_lay)
        card_lay.addWidget(tip_label)
        card_lay.addWidget(self.keyboard, alignment=Qt.AlignCenter)
        card_lay.addLayout(btn_lay)

        main_lay.addWidget(card, alignment=Qt.AlignCenter)
        main_lay.addStretch(1)
        self.setLayout(main_lay)

        self.btn_save.clicked.connect(self.save_data)
        self.btn_back.clicked.connect(self.go_back_home)

    def go_back_home(self):
        fit_screen_and_fullscreen(self.home)
        self.close()

    def save_data(self):
        code = self.edit_code.text().strip()
        position = self.edit_pos.text().strip()

        if not code or not position:
            QMessageBox.warning(self, "输入提示", "位置码和存放位置都不能为空！")
            return

        for item in global_express_data:
            if item["code"] == code:
                QMessageBox.warning(self, "录入失败", "该位置码已存在，请勿重复录入！")
                return

        global_express_data.append({"code": code, "position": position})
        QMessageBox.information(self, "录入成功", f"位置码 {code} 已添加成功！")
        self.edit_code.clear()
        self.edit_pos.clear()
        self.edit_code.setFocus()

# ====================== 程序入口（统一全屏适配 + 启动串口线程） ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont()
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    home_win = HomeWindow()
    query_win = QueryWindow(home_win)
    add_win = AddWindow(home_win)
    patrol_win = PatrolWindow(home_win)

    # 初始化串口后台线程
    serial_thread = SerialThread()
    # 串口报警信号绑定首页弹窗函数
    serial_thread.sig_alarm.connect(home_win.show_safety_alert_from_serial)
    serial_thread.start()

    # 页面跳转函数
    def open_query_page():
        fit_screen_and_fullscreen(query_win)
        home_win.close()

    def open_add_page():
        fit_screen_and_fullscreen(add_win)
        home_win.close()

    def open_patrol_page():
        fit_screen_and_fullscreen(patrol_win)
        home_win.close()

    home_win.btn_query.clicked.connect(open_query_page)
    home_win.btn_add.clicked.connect(open_add_page)
    home_win.btn_patrol.clicked.connect(open_patrol_page)

    # 启动首页全屏
    fit_screen_and_fullscreen(home_win)
    exit_code = app.exec_()
    # 退出程序关闭串口线程，释放串口
    serial_thread.stop()
    sys.exit(exit_code)
