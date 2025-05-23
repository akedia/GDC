# WAV文件重命名工具使用说明

## 概述
这套工具用于将处理后的WAV文件名称还原成标准的GDC演讲文件名称。

## 文件说明

### 主要脚本
1. **rename_wav_files_v3.py** - 主要的匹配脚本，生成重命名预览
2. **execute_rename_v3.py** - 执行实际的重命名操作

### 其他版本（保留供参考）
- rename_wav_files.py - 初始版本
- rename_wav_files_v2.py - 第二版本
- execute_rename.py - 对应v2版本的执行脚本

## 使用步骤

### 第一步：生成预览
```bash
cd D:\GDC
python rename_wav_files_v3.py
```

这会生成两个文件：
- `wav_rename_preview_v3.txt` - 人类可读的预览文件
- `wav_rename_preview_v3.json` - 供执行脚本使用的JSON格式文件

### 第二步：检查预览结果
打开 `wav_rename_preview_v3.txt` 文件，检查匹配结果是否正确。

### 第三步：执行重命名
如果预览结果满意，执行：
```bash
python execute_rename_v3.py
```

选择选项 1 执行重命名。

## 功能特点

1. **智能匹配算法**
   - 基于字符串相似度的自动匹配
   - 关键词提取和匹配
   - 特殊术语处理（如 WoW -> World of Warcraft）

2. **手动映射**
   - 对于难以自动匹配的文件，脚本包含手动映射表
   - 确保100%的匹配率

3. **安全机制**
   - 自动备份原文件到带时间戳的备份目录
   - 跳过已存在的目标文件，避免覆盖
   - 支持从备份恢复

4. **日志记录**
   - 生成详细的操作日志
   - 记录成功、跳过和错误的文件数量

## 恢复备份
如果需要恢复原文件名：
```bash
python execute_rename_v3.py
```
选择选项 2，然后选择要恢复的备份目录。

## 注意事项
- 确保在执行重命名前检查预览结果
- 备份文件会保存在 `backup_YYYYMMDD_HHMMSS` 格式的目录中
- 操作日志会保存在 `rename_log_YYYYMMDD_HHMMSS.txt` 文件中 