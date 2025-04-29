import os
import shutil
import sys

def flatten_directory(directory):
    """
    将指定目录下的所有子文件夹中的文件移动到该目录下，并删除空的子文件夹
    """
    # 确保目录存在
    if not os.path.exists(directory) or not os.path.isdir(directory):
        print(f"错误: {directory} 不是一个有效的目录")
        return False

    # 获取所有子文件夹
    subfolders = [f.path for f in os.scandir(directory) if f.is_dir()]
    
    # 遍历每个子文件夹
    for subfolder in subfolders:
        print(f"处理子文件夹: {subfolder}")
        
        # 遍历子文件夹中的所有文件
        for root, _, files in os.walk(subfolder):
            for file in files:
                source_path = os.path.join(root, file)
                dest_path = os.path.join(directory, file)
                
                # 检查目标路径是否已存在文件
                if os.path.exists(dest_path):
                    # 如果存在同名文件，添加文件夹名作为前缀
                    folder_name = os.path.basename(subfolder)
                    new_filename = f"{folder_name}_{file}"
                    dest_path = os.path.join(directory, new_filename)
                    print(f"文件名冲突: {file} 已重命名为 {new_filename}")
                
                # 移动文件
                try:
                    shutil.move(source_path, dest_path)
                    print(f"已移动: {source_path} -> {dest_path}")
                except Exception as e:
                    print(f"移动文件时出错: {e}")
        
        # 删除空的子文件夹
        try:
            # 检查是否还有子文件夹
            if not any(os.scandir(subfolder)):
                os.rmdir(subfolder)
                print(f"已删除空文件夹: {subfolder}")
            else:
                # 递归处理子文件夹内的子文件夹
                flatten_directory(subfolder)
        except Exception as e:
            print(f"删除文件夹时出错: {e}")

if __name__ == "__main__":
    # 默认使用当前目录下的2024文件夹
    target_dir = "2024"
    
    # 如果提供了命令行参数，则使用指定的目录
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    
    # 确保目录使用绝对路径
    if not os.path.isabs(target_dir):
        target_dir = os.path.abspath(target_dir)
    
    print(f"开始平铺目录: {target_dir}")
    flatten_directory(target_dir)
    print("完成目录平铺操作") 