import os
import io
import pickle
from collections import defaultdict # 导入 defaultdict
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# --- 配置 ---
SCOPES = ['https://www.googleapis.com/auth/drive'] # 权限范围，允许完全控制 Drive 文件
CLIENT_SECRETS_FILE = 'client_secrets.json' # OAuth 凭证文件路径
TOKEN_PICKLE_FILE = 'token.pickle'          # 存储授权令牌的文件路径
SOURCE_FOLDER_PATH = './2025'       # 本地源文件夹路径 (请修改为你的实际路径)
TARGET_DRIVE_FOLDER_NAME = 'GDC 2025' # Google Drive 目标文件夹名称 (请修改)
# --- 配置结束 ---

def authenticate_google_drive():
    """处理 Google Drive API 的认证流程"""
    creds = None
    # token.pickle 文件存储用户的访问和刷新令牌，
    # 并在第一次授权后自动创建。
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)
    # 如果没有有效凭证，让用户登录。
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            # 注意：这里会打开浏览器让用户授权
            creds = flow.run_local_server(port=0)
        # 保存凭证供下次运行
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name, parent_id=None):
    """查找或创建 Google Drive 文件夹"""
    # 转义文件夹名称中的单引号，以用于查询
    escaped_folder_name = folder_name.replace("'", "\\'")

    query = f"mimeType='application/vnd.google-apps.folder' and name='{escaped_folder_name}' and trashed=false"
    effective_parent_id = parent_id if parent_id else 'root' # 确定查询的父级
    query += f" and '{effective_parent_id}' in parents"

    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = response.get('files', [])

    if folders:
        print(f"  找到文件夹 '{folder_name}' (ID: {folders[0]['id']}) (父级: {effective_parent_id})")
        return folders[0]['id']
    else:
        print(f"  未找到文件夹 '{folder_name}' (父级: {effective_parent_id})，正在创建...")
        # 注意：创建文件夹时，body 中的 name 仍然使用原始的、未转义的名称
        file_metadata = {
            'name': folder_name, # 使用原始名称创建
            'mimeType': 'application/vnd.google-apps.folder'
        }
        # 只有在指定了非 root 的 parent_id 时才添加 parents 字段
        # 否则默认为 root
        if parent_id:
            file_metadata['parents'] = [parent_id]
        else:
            # 如果 parent_id 为 None，则创建在根目录，不需要指定 parents
            pass
        try:
            folder = service.files().create(body=file_metadata, fields='id').execute()
            new_folder_id = folder.get('id')
            print(f"  已创建文件夹 '{folder_name}' (ID: {new_folder_id}) (父级: {effective_parent_id})")
            return new_folder_id
        except Exception as e:
            print(f"  创建文件夹 '{folder_name}' 时出错: {e}")
            return None

def get_drive_files_in_folder(service, folder_id):
    """获取指定 Drive 文件夹下的所有文件和子文件夹"""
    files_in_drive = {}
    page_token = None
    while True:
        try:
            response = service.files().list(q=f"'{folder_id}' in parents and trashed=false",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name, mimeType)',
                                              pageToken=page_token).execute()
            for file_item in response.get('files', []):
                base_name, _ = os.path.splitext(file_item['name'])
                if base_name not in files_in_drive:
                    files_in_drive[base_name] = []
                files_in_drive[base_name].append(file_item)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        except Exception as e:
            print(f"获取 Drive 文件夹 {folder_id} 内容时出错: {e}")
            # 可以选择重试或直接返回空字典/部分结果
            return {}
    return files_in_drive


def upload_file(service, file_path, parent_folder_id):
    """上传单个文件到指定的 Drive 文件夹，上传前检查是否存在同名文件"""
    file_name = os.path.basename(file_path)
    print(f"    准备上传: '{file_name}' 到文件夹 ID: {parent_folder_id}")

    # 检查 Drive 中是否已存在同名文件
    try:
        # 转义文件名中的单引号以用于查询
        escaped_file_name = file_name.replace("'", "\\'")
        query = f"name='{escaped_file_name}' and '{parent_folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        existing_files = response.get('files', [])

        if existing_files:
            print(f"    跳过上传：文件 '{file_name}' 已存在于目标文件夹 (ID: {existing_files[0]['id']})。")
            return existing_files[0]['id'] # 返回已存在文件的 ID
        else:
            print(f"    检查完成：目标文件夹中无同名文件，开始上传...")
            # 文件不存在，执行上传
            file_metadata = {'name': file_name, 'parents': [parent_folder_id]}
            media = MediaFileUpload(file_path, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"    上传成功: '{file_name}' (新 ID: {file.get('id')})")
            return file.get('id')

    except Exception as e:
        print(f"    在检查或上传文件 '{file_name}' 时出错: {e}")
        return None

def move_file(service, file_id, file_name, current_parent_id, new_parent_id):
    """将文件移动到新的父文件夹"""
    print(f"    正在移动文件 '{file_name}' (ID: {file_id}) 从父级 {current_parent_id} 到 {new_parent_id}...")
    try:
        # 从 service.files().get() 获取文件以查找所有父级
        file_details = service.files().get(fileId=file_id, fields='parents').execute()
        # previous_parents = ",".join(file_details.get('parents'))
        # ^^^ Google API 文档建议只移除我们知道的那个父级 ID
        # 特别是当文件可能在多个父级下时（尽管 Drive UI 不鼓励这样做）

        # 移动文件
        service.files().update(fileId=file_id,
                               addParents=new_parent_id,
                               removeParents=current_parent_id, # 只移除我们知道的当前父级
                               fields='id, parents').execute()
        print(f"    移动成功: 文件 '{file_name}' 已移至文件夹 ID {new_parent_id}")
        return True
    except Exception as e:
        print(f"    移动文件 '{file_name}' (ID: {file_id}) 时出错: {e}")
        return False

def main():
    """主函数，执行认证、获取文件夹、上传文件逻辑"""
    service = authenticate_google_drive()

    # 1. 获取或创建目标 Drive 文件夹 (根目录下的)
    print("步骤 1: 获取或创建目标 Drive 文件夹")
    target_folder_id = get_or_create_folder(service, TARGET_DRIVE_FOLDER_NAME, parent_id=None)
    if not target_folder_id:
        print("错误：无法获取或创建目标 Google Drive 文件夹，脚本终止。")
        return

    # 2. 检查本地源文件夹是否存在
    print("\n步骤 2: 检查本地源文件夹")
    if not os.path.isdir(SOURCE_FOLDER_PATH):
        print(f"错误：本地源文件夹 '{SOURCE_FOLDER_PATH}' 不存在或不是一个目录。")
        return
    print(f"本地源文件夹 '{SOURCE_FOLDER_PATH}' 存在。")

    # 3. 预扫描本地文件夹，统计基础文件名计数
    print("\n步骤 3: 预扫描本地文件以确定同名文件组")
    local_basename_counts = defaultdict(int)
    local_files_to_process = []
    for item_name in os.listdir(SOURCE_FOLDER_PATH):
        local_item_path = os.path.join(SOURCE_FOLDER_PATH, item_name)
        if os.path.isfile(local_item_path):
            base_name, _ = os.path.splitext(item_name)
            local_basename_counts[base_name] += 1
            local_files_to_process.append((item_name, local_item_path, base_name))
        # else: # 如果需要处理本地子目录，在这里添加逻辑
        #     print(f"跳过本地子目录: {item_name}")
    print(f"本地文件扫描完成。发现 {len(local_files_to_process)} 个文件。")
    # 打印需要创建子文件夹的组（调试用）
    duplicate_bases = {base for base, count in local_basename_counts.items() if count > 1}
    if duplicate_bases:
        print(f"根据本地文件，以下基础文件名 ('{len(duplicate_bases)}' 个) 需要创建或检查子文件夹。") # 简化打印
    else:
        print("根据本地文件，没有需要创建子文件夹的同名文件组。")

    # 4. 获取目标 Drive 文件夹内已存在的文件/文件夹信息
    print(f"\n步骤 4: 获取 Drive 目标文件夹 '{TARGET_DRIVE_FOLDER_NAME}' (ID: {target_folder_id}) 的当前内容")
    drive_contents = get_drive_files_in_folder(service, target_folder_id)
    print(f"目标文件夹内容获取完成。")

    # 5. 遍历处理本地文件列表
    print(f"\n步骤 5: 开始处理和上传文件")
    processed_subfolders = {} # 存储在本轮运行中确定/创建的子文件夹 {basename: folder_id}

    for item_name, local_item_path, base_name in local_files_to_process:
        print(f"\n处理本地文件: '{item_name}' (基础名: '{base_name}')")

        # 确定此文件是否应放入子文件夹（基于本地计数）
        needs_subfolder = local_basename_counts[base_name] > 1
        destination_parent_id = None
        subfolder_id_to_use = None

        if needs_subfolder:
            print(f"  判定: 此基础文件名 ('{base_name}') 在本地出现多次，需要放入子文件夹。")
            # 检查是否已处理过这个子文件夹
            if base_name in processed_subfolders:
                subfolder_id_to_use = processed_subfolders[base_name]
                print(f"  使用已处理的子文件夹 ID: {subfolder_id_to_use}")
            else:
                print(f"  首次处理基础文件名 '{base_name}' 的子文件夹。")
                # 查找或创建 Drive 子文件夹
                subfolder_id_to_use = get_or_create_folder(service, base_name, target_folder_id)
                if subfolder_id_to_use:
                    processed_subfolders[base_name] = subfolder_id_to_use
                    # 将 Drive 目标文件夹根目录下已存在的同基础名文件移入子文件夹
                    # (注意：这里移动的是目标文件夹根目录下的文件，子文件夹内的同名文件不影响)
                    existing_files_in_root = [f for f in drive_contents.get(base_name, [])
                                              if f['mimeType'] != 'application/vnd.google-apps.folder']
                    if existing_files_in_root:
                        print(f"  发现 {len(existing_files_in_root)} 个同基础名的文件在目标文件夹根目录，将移动它们到子文件夹 '{base_name}'。")
                        for drive_file in existing_files_in_root:
                            # 在移动前再次确认文件确实在 target_folder_id 下 (可选但更安全)
                            file_details_for_move = service.files().get(fileId=drive_file['id'], fields='parents').execute()
                            if target_folder_id in file_details_for_move.get('parents', []):
                                move_file(service, drive_file['id'], drive_file['name'], target_folder_id, subfolder_id_to_use)
                            else:
                                print(f"    警告: 文件 '{drive_file['name']}' (ID: {drive_file['id']}) 不在预期的父级 {target_folder_id} 下，跳过移动。")
                    else:
                        print(f"  目标文件夹根目录无已存在的同基础名文件需要移动。")
                else:
                    print(f"  错误：无法为 '{base_name}' 获取或创建子文件夹，跳过文件 '{item_name}'")
                    continue # 跳过此文件
            destination_parent_id = subfolder_id_to_use

        else: # 本地只有一个同名文件
            print(f"  判定: 此基础文件名 ('{base_name}') 在本地仅出现一次。")
            # 检查 Drive 上是否有冲突（已存在的同名子文件夹或文件）
            existing_drive_items = drive_contents.get(base_name, [])
            existing_subfolder_in_drive = next((f for f in existing_drive_items if f['mimeType'] == 'application/vnd.google-apps.folder' and f['name'] == base_name), None)
            existing_files_in_drive_root = [f for f in existing_drive_items if f['mimeType'] != 'application/vnd.google-apps.folder']

            if existing_subfolder_in_drive:
                print(f"  冲突：Drive 上已存在同名子文件夹 (ID: {existing_subfolder_in_drive['id']})。将尝试上传到此子文件夹。")
                subfolder_id_to_use = existing_subfolder_in_drive['id']
                # 记录下来，以防万一
                if base_name not in processed_subfolders:
                    processed_subfolders[base_name] = subfolder_id_to_use
                destination_parent_id = subfolder_id_to_use
            elif existing_files_in_drive_root:
                print(f"  冲突：Drive 上目标文件夹根目录已存在 {len(existing_files_in_drive_root)} 个同名文件。将创建子文件夹并移入。")
                # 这种情况，我们强制创建子文件夹并移动
                subfolder_id_to_use = get_or_create_folder(service, base_name, target_folder_id)
                if subfolder_id_to_use:
                    if base_name not in processed_subfolders:
                         processed_subfolders[base_name] = subfolder_id_to_use
                    for drive_file in existing_files_in_drive_root:
                         # 同样，移动前确认父级
                        file_details_for_move = service.files().get(fileId=drive_file['id'], fields='parents').execute()
                        if target_folder_id in file_details_for_move.get('parents', []):
                            move_file(service, drive_file['id'], drive_file['name'], target_folder_id, subfolder_id_to_use)
                        else:
                             print(f"    警告: 文件 '{drive_file['name']}' (ID: {drive_file['id']}) 不在预期的父级 {target_folder_id} 下，跳过移动。")
                    destination_parent_id = subfolder_id_to_use
                else:
                    print(f"  错误：无法为冲突文件 '{base_name}' 创建子文件夹，跳过文件 '{item_name}'")
                    continue # 跳过此文件
            else:
                print(f"  无冲突：将尝试直接上传到目标文件夹 '{TARGET_DRIVE_FOLDER_NAME}'。")
                destination_parent_id = target_folder_id

        # 执行上传（upload_file 内部会进行存在性检查）
        if destination_parent_id:
            upload_file(service, local_item_path, destination_parent_id)
        else:
             # 这个分支理论上不应该到达，除非 get_or_create_folder 失败且未 continue
             print(f"  错误：无法确定文件 '{item_name}' 的目标文件夹，跳过上传。")

    print("\n所有文件处理完毕。")

if __name__ == '__main__':
    main() 