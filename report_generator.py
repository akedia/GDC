import os
import re
from urllib.parse import quote
from upload_to_drive import authenticate_google_drive, SOURCE_FOLDER_PATH

REPORT_FILE = 'report_new.md'

def slugify(title):
    """将标题转换为 Markdown 锚点格式的小写短链接"""
    s = title.lower()
    s = s.replace("'", "")
    s = s.replace(" ", "-")
    s = re.sub(r'[^a-z0-9\-_]', '', s)
    return s

def main():
    service = authenticate_google_drive()
    entries = []

    # 遍历所有子目录，查找 .txt 文件
    for root, dirs, files in os.walk(SOURCE_FOLDER_PATH):
        for file in files:
            if file.lower().endswith('.txt'):
                relative_folder = os.path.relpath(root, SOURCE_FOLDER_PATH)
                txt_path = os.path.join(root, file)
                # 读取摘要内容
                with open(txt_path, 'r', encoding='utf-8') as f:
                    summary = f.read().strip()
                base_name = os.path.splitext(file)[0]

                # 对 base_name 中的单引号进行转义
                escaped_base_name = base_name.replace("'", "\\'")

                # 在 Google Drive 中搜索对应的视频文件
                query = f"name contains '{escaped_base_name}' and mimeType contains 'video/' and trashed=false"
                response = service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)',
                    pageSize=1
                ).execute()
                items = response.get('files', [])

                if items:
                    file_id = items[0]['id']
                    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                else:
                    link = '未找到对应视频文件'

                # 查找同名 png 文件
                png_file = os.path.join(root, f'{base_name}.png')
                if os.path.exists(png_file):
                    # 考虑报告文件与SOURCE_FOLDER_PATH的相对位置
                    # 获取包含SOURCE_FOLDER_PATH的绝对路径
                    source_abs_path = os.path.abspath(SOURCE_FOLDER_PATH)
                    # 获取报告文件所在的绝对路径
                    report_dir_abs_path = os.path.dirname(os.path.abspath(REPORT_FILE))
                    # 计算SOURCE_FOLDER_PATH相对于报告文件目录的路径
                    source_rel_to_report = os.path.relpath(source_abs_path, report_dir_abs_path)
                    
                    if relative_folder == '.':
                        png_path = os.path.join(source_rel_to_report, f'{base_name}.png').replace('\\', '/')
                    else:
                        png_path = os.path.join(source_rel_to_report, relative_folder, f'{base_name}.png').replace('\\', '/')
                else:
                    png_path = None

                entries.append({
                    'title': base_name,
                    'relative_folder': relative_folder,
                    'video_link': link,
                    'summary': summary,
                    'png_path': png_path
                })

    # 生成报告
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('# GDC 2025 合并报告\n\n')
        f.write('## 目录\n\n')
        for idx, e in enumerate(entries, 1):
            slug = slugify(e['title'])
            f.write(f"{idx}. [{e['title']}](#{slug}) - {e['relative_folder']}\n")
        f.write('\n')

        for idx, e in enumerate(entries, 1):
            slug = slugify(e['title'])
            f.write('---\n\n')
            f.write(f'<h3 id="{slug}">{e["title"]}</h3>\n\n')
            f.write(f"- 视频链接: [{e['video_link']}]({e['video_link']})\n\n")
            f.write('**摘要**:\n\n')
            f.write(e['summary'] + '\n\n')
            if e.get('png_path'):
                png_url = quote(e['png_path'], safe='/')
                f.write(f"![{e['title']} 截图]({png_url})\n\n")

    print(f"报告已生成: {REPORT_FILE}")


if __name__ == '__main__':
    main() 