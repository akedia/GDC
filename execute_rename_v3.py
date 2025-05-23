import os
import json
import shutil
from datetime import datetime

def execute_rename():
    """执行重命名操作"""
    # 设置工作目录
    work_dir = r"D:\GDC\2025"
    os.chdir(work_dir)
    
    # 读取预览文件
    preview_file = 'wav_rename_preview_v3.json'
    
    if not os.path.exists(preview_file):
        print("错误：找不到预览文件 wav_rename_preview_v3.json")
        print("请先运行 rename_wav_files_v3.py 生成预览文件")
        return
    
    with open(preview_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    matches = data['matches']
    
    print(f"准备重命名 {len(matches)} 个文件")
    print("-" * 80)
    
    # 创建备份目录
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    print(f"备份目录已创建: {backup_dir}\n")
    
    # 执行重命名
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, match in enumerate(matches, 1):
        old_path = match['old']
        new_path = match['new']
        
        print(f"\n[{i}/{len(matches)}] 处理: {old_path}")
        print(f"  -> {new_path}")
        
        try:
            # 检查原文件是否存在
            if not os.path.exists(old_path):
                print(f"  ❌ 错误: 原文件不存在")
                error_count += 1
                continue
            
            # 检查新文件名是否已存在
            if os.path.exists(new_path):
                print(f"  ⚠️  警告: 目标文件已存在，跳过")
                skip_count += 1
                continue
            
            # 备份原文件
            backup_path = os.path.join(backup_dir, old_path)
            shutil.copy2(old_path, backup_path)
            
            # 重命名文件
            os.rename(old_path, new_path)
            print(f"  ✅ 成功")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            error_count += 1
    
    # 打印统计信息
    print("\n" + "=" * 80)
    print("重命名完成！")
    print(f"成功: {success_count} 个文件")
    print(f"跳过: {skip_count} 个文件（目标文件已存在）")
    print(f"错误: {error_count} 个文件")
    print(f"\n原文件已备份到: {backup_dir}")
    
    # 生成操作日志
    log_file = f"rename_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("WAV文件重命名操作日志\n")
        f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"总计: {len(matches)} 个文件\n")
        f.write(f"成功: {success_count} 个\n")
        f.write(f"跳过: {skip_count} 个\n")
        f.write(f"错误: {error_count} 个\n")
        f.write(f"备份目录: {backup_dir}\n")
        
        f.write("\n\n详细日志：\n")
        f.write("-" * 80 + "\n")
        for match in matches:
            f.write(f"{match['old']} -> {match['new']}\n")
    
    print(f"\n操作日志已保存到: {log_file}")

def restore_backup():
    """从备份恢复文件"""
    print("可用的备份目录：")
    backup_dirs = [d for d in os.listdir('.') if d.startswith('backup_') and os.path.isdir(d)]
    
    if not backup_dirs:
        print("没有找到备份目录")
        return
    
    for i, d in enumerate(backup_dirs, 1):
        print(f"{i}. {d}")
    
    choice = input("\n选择要恢复的备份目录编号（输入0取消）: ")
    
    try:
        choice = int(choice)
        if choice == 0:
            print("取消恢复")
            return
        
        if 1 <= choice <= len(backup_dirs):
            backup_dir = backup_dirs[choice - 1]
            
            # 恢复文件
            files = os.listdir(backup_dir)
            for f in files:
                src = os.path.join(backup_dir, f)
                dst = f
                shutil.copy2(src, dst)
                print(f"恢复: {f}")
            
            print(f"\n成功从 {backup_dir} 恢复 {len(files)} 个文件")
        else:
            print("无效的选择")
    
    except ValueError:
        print("请输入有效的数字")

if __name__ == "__main__":
    print("WAV文件批量重命名工具 (版本3)")
    print("1. 执行重命名")
    print("2. 从备份恢复")
    
    choice = input("\n请选择操作 (1/2): ")
    
    if choice == '1':
        execute_rename()
    elif choice == '2':
        os.chdir(r"D:\GDC\2025")
        restore_backup()
    else:
        print("无效的选择") 