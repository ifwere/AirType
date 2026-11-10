import os
import subprocess
import sys
from PIL import Image, ImageDraw

def create_round_rect_icon():
    print("Generating Dark Mode icon (macOS Standard Size)...")
    
    # 1. 画布设置
    size = 1024
    
    # --- 修复核心：缩放比例 ---
    # macOS Big Sur+ 规范：内容区域约为画布的 80%-82%
    # 这样生成的图标在 Dock 上才会和其他应用一样大
    scale_factor = 0.82 
    
    # 计算实际背景矩形的尺寸
    icon_size = size * scale_factor
    margin = (size - icon_size) / 2
    
    # 背景色：深炭灰
    bg_color = '#2b2b2b' 
    # 强调色：柔和的青蓝色
    accent_color = '#4dabf7' 
    
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 2. 绘制底座 (macOS 风格圆角矩形)
    # 这里的坐标不再是 (0,0) 到 (1024,1024)，而是缩进后的坐标
    rect_coords = [margin, margin, size - margin, size - margin]
    
    # 圆角半径也要相应调整，通常是图标本体尺寸的 22% 左右
    radius = icon_size * 0.22
    
    # 绘制深色背景
    draw.rounded_rectangle(rect_coords, radius=radius, fill=bg_color)
    
    # 3. 绘制简单的 "输入" 图标
    # 中心点不变，依然是 512, 512
    center_x, center_y = size // 2, size // 2
    
    # 为了配合缩小的背景，内部的符号也稍微缩小一点点 (乘以 0.9) 看起来更协调
    symbol_scale = 0.9
    
    # 3.1 绘制左边的箭头 ">"
    line_width = 60 * symbol_scale
    arrow_size = 180 * symbol_scale
    arrow_left_x = center_x - (200 * symbol_scale)
    
    # 上半撇
    draw.line(
        [(arrow_left_x, center_y - arrow_size), (arrow_left_x + arrow_size, center_y)], 
        fill='white', width=int(line_width), joint='curve'
    )
    # 下半撇
    draw.line(
        [(arrow_left_x, center_y + arrow_size), (arrow_left_x + arrow_size, center_y)], 
        fill='white', width=int(line_width), joint='curve'
    )
    
    # 3.2 绘制右边的光标 "_"
    cursor_w = 180 * symbol_scale
    cursor_h = line_width
    cursor_x = center_x + (50 * symbol_scale)
    cursor_y = center_y + arrow_size - cursor_h / 2 
    
    draw.rounded_rectangle(
        [cursor_x, cursor_y, cursor_x + cursor_w, cursor_y + cursor_h],
        radius=10, fill=accent_color
    )

    # 4. 保存 PNG
    img.save('icon.png')
    print("Saved icon.png")
    
    # 5. 生成 macOS .icns
    if sys.platform == 'darwin':
        iconset_name = 'AirType.iconset'
        if os.path.exists(iconset_name):
            import shutil
            shutil.rmtree(iconset_name)
        os.makedirs(iconset_name)

        sizes = [16, 32, 128, 256, 512, 1024]
        for s in sizes:
            resized = img.resize((s, s), Image.Resampling.LANCZOS)
            resized.save(f"{iconset_name}/icon_{s}x{s}.png")
            if s * 2 <= 1024:
                resized_2x = img.resize((s*2, s*2), Image.Resampling.LANCZOS)
                resized_2x.save(f"{iconset_name}/icon_{s}x{s}@2x.png")
        
        try:
            subprocess.run(['iconutil', '-c', 'icns', iconset_name, '-o', 'icon.icns'], check=True)
            print("Generated icon.icns successfully.")
        except Exception as e:
            print(f"Error generating .icns: {e}")
        
        import shutil
        shutil.rmtree(iconset_name)

if __name__ == '__main__':
    create_round_rect_icon()