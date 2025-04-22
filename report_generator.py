import os
import re # 导入 re 模块用于生成锚点
import urllib.parse # 导入 urllib.parse 用于 URL 编码
from upload_to_drive import authenticate_google_drive, SOURCE_FOLDER_PATH

REPORT_FILE = 'report.md'

def generate_anchor(text):
    """根据文本生成 Markdown 锚点 (slug)"""
    # 转换为小写
    text = text.lower()
    # 移除特殊字符，只保留字母、数字、空格和连字符
    text = re.sub(r'[^\w\s-]', '', text)
    # 将空格替换为连字符
    text = re.sub(r'\s+', '-', text)
    # 移除首尾可能出现的连字符
    text = text.strip('-')
    return text

def main():
    service = authenticate_google_drive()
    entries = []

    # 遍历所有子目录，查找 .txt 文件
    for root, dirs, files in os.walk(SOURCE_FOLDER_PATH):
        # 跳过根目录本身的处理逻辑，如果根目录也需要处理则移除此判断
        if root == SOURCE_FOLDER_PATH:
            print(f"扫描根目录: {root}")
        else:
            print(f"扫描子目录: {root}")

        # 收集当前目录下的 txt 和 png 文件基础名
        txt_files = {os.path.splitext(f)[0]: f for f in files if f.lower().endswith('.txt')}
        png_files = {os.path.splitext(f)[0]: f for f in files if f.lower().endswith('.png')}

        for base_name, txt_file in txt_files.items():
            relative_folder = os.path.relpath(root, SOURCE_FOLDER_PATH)
            # 处理根目录下的文件情况，避免 relative_folder 为 '.'
            if relative_folder == '.':
                relative_folder = '' # 或者根据需要设置为根目录名

            txt_path = os.path.join(root, txt_file)
            png_file_name = png_files.get(base_name) # 查找同基础名的 png 文件
            png_relative_path = None
            if png_file_name:
                # 构建相对于 report.md 的路径
                png_relative_path = os.path.join(relative_folder, png_file_name).replace('\\', '/') # 确保使用 / 作为路径分隔符

            # 读取摘要内容
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    summary = f.read().strip()
            except Exception as e:
                print(f"  读取摘要文件 '{txt_path}' 时出错: {e}")
                summary = "读取摘要失败" # 提供默认值或跳过

            # --- Google Drive 链接查找 ---
            escaped_base_name = base_name.replace("'", "\\\\'") # Correct escaping for Drive API query
            link = '未找到对应视频文件' # 默认值
            try:
                # 仅精确搜索名称包含基础名且 MIME 类型为视频的文件
                query_video = f"name contains '{escaped_base_name}' and mimeType contains 'video/' and trashed=false"
                print(f"  查询 Drive 视频: {query_video}") # 添加调试打印

                response_video = service.files().list(
                    q=query_video, spaces='drive', fields='files(id, name, webViewLink)', pageSize=1 # 限制为1个结果
                ).execute()
                items_video = response_video.get('files', [])

                if items_video:
                    video_file = items_video[0]
                    file_id = video_file['id']
                    # 优先使用 webViewLink，否则构建标准链接
                    link = video_file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view?usp=sharing")
                    print(f"  找到 Drive 视频文件: '{video_file['name']}' (ID: {file_id}) -> 链接: {link}")
                else:
                    # 如果找不到视频文件，则保持 link 为 '未找到对应视频文件'
                    print(f"  未在 Drive 中找到与 '{base_name}' 匹配的视频文件。")
                    # 不再执行后备搜索

            except Exception as e:
                 print(f"  在 Drive 中搜索视频 '{base_name}' 时出错: {e}")
                 # 可以在链接中直接反映错误，或者保持"未找到"
                 link = f'搜索视频文件时出错' # 例如，更新链接以反映错误状态

            # --- Google Drive 链接查找结束 ---


            entries.append({
                'title': base_name,
                'relative_folder': relative_folder if relative_folder else '根目录',
                'anchor': generate_anchor(base_name),
                'link': link, # 此处 link 要么是视频链接，要么是"未找到"或错误信息
                'summary': summary,
                'png_path': png_relative_path
            })

    # 对 entries 进行排序，可以按文件夹或标题排序
    entries.sort(key=lambda x: (x['relative_folder'], x['title']))


    # 生成报告
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('# 合并报告\n\n')
        f.write('## 目录\n\n')
        current_folder = None
        for idx, e in enumerate(entries, 1):
             # 添加文件夹层级
            if e['relative_folder'] != current_folder:
                if current_folder is not None: # 避免在第一个文件夹前加空行
                    f.write('\n') # 在新文件夹前加空行
                f.write(f"**{e['relative_folder']}**\n\n") # 加粗显示文件夹名
                current_folder = e['relative_folder']
            # 使用内部锚点链接
            f.write(f"- [{e['title']}](#{e['anchor']})\n") # 索引序号可选

        f.write('\n') # 目录结束后加空行

        for e in entries:
            f.write('---\n\n')
            # 添加锚点
            f.write(f"### {e['title']}\n\n")
            f.write(f"- **本地路径:** {e['relative_folder']}\n")
            # 使用尖括号将 Google Drive 链接标记为自动链接
            if e['link'] != '未找到对应视频文件': # 只对有效链接应用格式
                f.write(f"- **Google Drive 链接:** <{e['link']}>\n\n")
            else:
                f.write(f"- **Google Drive 链接:** {e['link']}\n\n") # 对未找到的情况保持原样
            f.write('**摘要:**\n\n')
            f.write(e['summary'] + '\n\n')
            # 嵌入 PNG 图片
            if e['png_path']:
                f.write('**截图:**\n\n')
                # 对文件路径进行 URL 编码
                encoded_png_path = urllib.parse.quote(e['png_path'])
                f.write(f"![{e['title']} 截图]({encoded_png_path})\n\n")
            else:
                f.write('**截图:** (未找到同名 PNG 文件)\n\n')


    print(f"报告已生成: {REPORT_FILE}")


if __name__ == '__main__':
    main() 