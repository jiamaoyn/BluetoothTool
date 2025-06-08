import math
import os
import struct
import sys
import asyncio

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QListWidget, QFileDialog, QLineEdit, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout
from bleak import BleakScanner, BleakClient

class BluetoothApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLE 蓝牙工具")
        self.setGeometry(300, 300, 800, 400)
        self.start_notify_flg = False
        self.devices = []
        self.service = []
        self.client = None
        self.selected_device = None
        self.selected_characteristic = None  # 添加这一行来初始化 selected_characteristic
        self.selected_file_path = None  # 保存选择的文件路径

        # layout = QVBoxLayout()
        # left_widget = QWidget()
        main_layout = QHBoxLayout()  # 替代原来的 QVBoxLayout
        # left_layout = QVBoxLayout(left_widget)  # 原有控件放这里
        # left_widget.setFixedWidth(300)  # 设置左侧区域宽度为 300

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(300)

        self.scan_button = QPushButton("扫描设备")
        self.scan_button.clicked.connect(self.scan_devices)
        left_layout.addWidget(self.scan_button)

        self.device_list = QListWidget()
        self.device_list.setFixedSize(300, 300)
        left_layout.addWidget(self.device_list)

        self.connect_button = QPushButton("连接所选设备")
        self.connect_button.clicked.connect(self.connect_device)
        left_layout.addWidget(self.connect_button)

        # self.status_label = QLabel("状态：未连接")
        # left_layout.addWidget(self.status_label)

        self.service_list = QListWidget()  # 新增控件展示服务
        left_layout.addWidget(self.service_list)

        # 新增按钮控件用于读、写、通知
        self.read_button = QPushButton("读取特征")
        self.read_button.clicked.connect(self.read_characteristic)
        left_layout.addWidget(self.read_button)

        self.write_input = QLineEdit()
        self.write_input.setPlaceholderText("输入要写入的数据")
        left_layout.addWidget(self.write_input)
        self.file_number_input = QLineEdit()
        self.file_number_input.setPlaceholderText("输入文件编号")
        left_layout.addWidget(self.file_number_input)

        self.write_button = QPushButton("写入数据")
        self.write_button.clicked.connect(self.write_characteristic)
        left_layout.addWidget(self.write_button)

        # 选择文件按钮
        self.choose_file_button = QPushButton("选择文件")
        self.choose_file_button.clicked.connect(self.choose_file)
        left_layout.addWidget(self.choose_file_button)

        # 发送文件按钮
        self.send_file_button = QPushButton("发送文件")
        self.send_file_button.clicked.connect(self.send_selected_file)
        left_layout.addWidget(self.send_file_button)

        # self.notify_button = QPushButton("开启通知")
        # self.notify_button.clicked.connect(self.start_notifications)
        # left_layout.addWidget(self.notify_button)

        main_layout.addWidget(left_widget)
        # 新增日志显示区域
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("日志输出区域")
        main_layout.addWidget(self.log_output, stretch=1)  # 占据右侧区域

        self.setLayout(main_layout)

    def append_log(self, message):
        self.log_output.append(message)
        print(message)  # 同时打印到控制台

    def select_characteristic(self, item):
        text = item.text().strip()
        if text.startswith("  └── [特征]"):
            try:
                uuid = text.split("[特征]")[1].split(",")[0].strip()
                self.selected_characteristic = uuid
                self.append_log(f"已选择特征: {uuid}")
            except Exception as e:
                self.append_log(f"解析特征失败: {str(e)}")
    def scan_devices(self):
        self.device_list.clear()
        self.append_log("状态：正在扫描...")
        asyncio.ensure_future(self._do_scan())

    async def _do_scan(self):
        self.devices = await BleakScanner.discover()
        for d in self.devices:
            self.device_list.addItem(f"{d.name or '未知设备'} [{d.address}]")
        self.append_log("状态：扫描完成")

    def connect_device(self):
        index = self.device_list.currentRow()
        if index < 0 or index >= len(self.devices):
            self.append_log("请选择一个设备")
            return

        device = self.devices[index]
        self.append_log(f"正在连接 {device.name or device.address}...")
        asyncio.ensure_future(self._do_connect(device))

    async def _do_connect(self, device):
        try:
            self.client = BleakClient(device)
            await self.client.connect()

            self.append_log(f"已连接: {device.name or device.address}")

            self.services = self.client.services
            self.service_list.clear()  # 清空之前的服务列表
            for service in self.services:
                service_info = f"[服务] {service.uuid} - {service.description or '无描述'}"
                self.service_list.addItem(service_info)
                for char in service.characteristics:
                    self.selected_characteristic = char.uuid
                    char_info = f"  └── [特征] {char.uuid}, 可读: {char.properties}"
                    self.service_list.addItem(char_info)

        except Exception as e:
            self.append_log(f"连接失败: {str(e)}")

    def read_characteristic(self):
        self.append_log("按钮点击，开始读取特征")
        if self.selected_characteristic:
            asyncio.ensure_future(self._read_characteristic(self.selected_characteristic))
        else:
            self.append_log("没有选择特征")

    async def _read_characteristic(self, characteristic):
        try:
            self.append_log(f"正在读取特征: {characteristic}")
            value = await self.client.read_gatt_char(characteristic)
            self.append_log(f"读取到的特征值: {value}")  # 打印返回值
            self.append_log(f"读取成功: {value}")
        except Exception as e:
            self.append_log(f"读取失败: {str(e)}")  # 打印错误信息

    def write_characteristic(self):
        self.append_log("按钮点击，开始写入特征")
        if self.selected_characteristic:
            data = bytes.fromhex(self.write_input.text())  # 转换为字节串
            asyncio.ensure_future(self._write_characteristic(self.selected_characteristic, data))
        else:
            self.append_log("没有选择特征")

    async def _write_characteristic(self, characteristic, data):
        try:
            self.append_log(f"尝试写入: {characteristic} -> {data}")
            await self.client.write_gatt_char(characteristic, data)
            self.append_log("写入成功")
        except Exception as e:
            self.append_log(f"写入失败: {str(e)}")

    def start_notifications(self):
        if self.selected_characteristic:
            if not self.start_notify_flg:
                asyncio.ensure_future(self._start_notifications(self.selected_characteristic))
            else:
                asyncio.ensure_future(self._stop_notifications(self.selected_characteristic))

    async def _start_notifications(self, characteristic):
        def notification_handler(sender: int, data: bytearray):
            self.append_log(f"收到通知: {data}")

        try:
            await self.client.start_notify(characteristic, notification_handler)
            self.append_log("通知已开启")
            self.start_notify_flg = True
            # self.notify_button.setText("关闭通知")
        except Exception as e:
            self.append_log(f"开启通知失败: {str(e)}")

    async def _stop_notifications(self, characteristic):
        try:
            await self.client.stop_notify(characteristic)
            self.start_notify_flg = False
            self.append_log("通知已关闭")
            # self.notify_button.setText("开启通知")
            self.append_log(f"已停止特征 {characteristic} 的通知")
        except Exception as e:
            self.append_log(f"关闭通知失败: {str(e)}")

    def choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要发送的文件", "", "所有文件 (*)")
        if file_path:
            self.selected_file_path = file_path
            self.append_log(f"已选择文件: {os.path.basename(file_path)}")
        else:
            self.append_log("未选择文件")

    def send_selected_file(self):
        if not self.selected_characteristic:
            self.append_log("请先选择特征")
            return

        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            self.append_log("未选择文件或文件不存在")
            return

        asyncio.ensure_future(self._send_file_in_chunks(self.selected_file_path))

    async def _send_file_in_chunks(self, file_path, chunk_size=247):
        file_number = int(self.file_number_input.text())
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            total = len(file_data)
            total_packets = math.ceil(total / chunk_size)
            self.append_log(f"文件大小: {total} 字节，将按 {chunk_size} 字节分包发送，需要分包: {total_packets} 包")
            # === 第0包：文件编号 ===
            header_payload = struct.pack(">H", file_number)
            header_frame = bytearray()
            header_frame.extend(b'\xAA\x55')  # 帧头
            header_frame.append(len(header_payload))  # 数据长度
            header_frame.append(0x05)  # 指令
            header_frame.extend(header_payload)  # 内容
            checksum = sum(header_frame[4:]) & 0xFF
            header_frame.append(checksum)
            await self.client.write_gatt_char(self.selected_characteristic, header_frame)
            self.append_log(f"✅ 已发送文件头包 (文件编号: {file_number})")

            for i in range(total_packets):
                start = i * chunk_size
                end = start + chunk_size
                payload = file_data[start:end]
                # 数据内容构建: [总包数 (2字节)] + [当前包号 (2字节)] + [实际数据]
                data_content = struct.pack(">HH", total_packets, i + 1) + payload  # 大端

                # 数据长度 = 指令 + 数据内容
                data_len = len(data_content)
                # 组装整个包：帧头 + 数据长度 + 指令 + 数据内容 + 校验和
                frame = bytearray()
                frame.extend(b'\xAA\x55')  # 帧头
                frame.append(data_len)  # 数据长度
                frame.append(0x05)  # 指令
                frame.extend(data_content)  # 数据内容

                # 计算校验和（从数据长度开始，到最后一个数据字节）
                checksum = sum(frame[4:]) & 0xFF
                frame.append(checksum)
                await self.client.write_gatt_char(self.selected_characteristic, frame)
                self.append_log(f"发送第 {i + 1}/{total_packets} 包: {frame.hex()}")
                await asyncio.sleep(0.05)  # 控制发送节奏

            self.append_log("文件发送完成")
        except Exception as e:
            self.append_log(f"文件发送失败: {str(e)}")
            self.append_log(f"错误: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = asyncio.get_event_loop()

    main_window = BluetoothApp()
    main_window.show()

    # 用异步事件循环与 Qt 集成
    from qasync import QEventLoop
    qloop = QEventLoop(app)
    asyncio.set_event_loop(qloop)

    with qloop:
        qloop.run_forever()
