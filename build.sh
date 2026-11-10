#!/bin/bash
set -e

# 1. 安装依赖 (确保环境干净)
# pip install -r requirements.txt

# 2. 生成图标
echo "Generating icons..."
python3.13 src/generate_icon.py

# 3. 清理
rm -rf build dist AirType.spec

# 4. 打包
# --add-data 语法: "源文件:目标路径"
# Mac 下分隔符是冒号 :

# 我指定python3.13是为了和mac默认的python3进行区分
pyinstaller --noconfirm --onedir --windowed --clean \
    --name "AirType" \
    --icon "icon.icns" \
    --add-data "icon.png:." \
    --osx-bundle-identifier "com.run.airtype" \
    src/remote_server.py

# 5. 签名 (可选，如果是本地运行不需要，分发给别人可能需要)
# codesign --deep --force --verbose --sign "-" dist/AirType.app

echo "Done. App is in dist/AirType.app"