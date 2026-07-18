汽水音乐广告自动点击器 通过 ADB + OpenCV 模板匹配，自动检测并点选 Qishui Music（汽水音乐）安卓应用中的广告。

博客 详细原理与使用教程：CSDN 博客

工作原理 ADB捕捉电话屏幕 OpenCV 匹配预先捕获的广告按钮模板 ADB在匹配坐标处模拟分流 智能倒计时过滤器避免计时器文本中的误报 完整循环：观看广告 ->领取奖励 ->继续 ->重复 前提条件 电话 启用开发者选项 - > USB 调试 通过USB连接到电脑

安装ADB（平台工具） https://developer.android.com/studio/releases/platform-tools 安装 Python 依赖 PIP install -r requirements.txt `

快速入门 Windows（双击） 档案 它的作用 setup.bat 一键安装（pip + adb 检查） start.bat 启动网页控制面板 
网页界面（推荐）  server.py

开放 http://127.0.0.1:8765 CLI Python main.py——现在

桌面图形界面（需要 tkinter） Python gui.py `

模板设置 点击网页面板中的“捕捉模板” 从截图中裁剪按钮区域 保存到铭牌/： 模板 描述 d_finished.png “申报成功”指示器 claim_reward.png “领取奖励”按钮 play_again.png “继续观看”按钮

许可 仅供教育用途。
