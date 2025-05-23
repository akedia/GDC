import os
import re
from difflib import SequenceMatcher
import json

def normalize_text(text):
    """标准化文本，用于更好的匹配"""
    # 转换为小写
    text = text.lower()
    # 移除标点符号（保留撇号）
    text = re.sub(r"[^\w\s']", " ", text)
    # 规范化空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_key_phrases(text):
    """提取关键短语"""
    # 一些常见的连接词，匹配时忽略
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = text.lower().split()
    # 过滤掉停用词
    key_words = [w for w in words if w not in stop_words]
    return set(key_words)

def calculate_match_score(wav_name, original_name):
    """计算更准确的匹配分数"""
    # 清理文件名
    wav_clean = os.path.splitext(wav_name)[0]
    orig_clean = original_name
    if orig_clean.startswith("GDC Vault - "):
        orig_clean = orig_clean[12:]
    
    # 标准化文本
    wav_norm = normalize_text(wav_clean)
    orig_norm = normalize_text(orig_clean)
    
    # 基础相似度
    base_score = SequenceMatcher(None, wav_norm, orig_norm).ratio()
    
    # 关键词匹配
    wav_keywords = extract_key_phrases(wav_clean)
    orig_keywords = extract_key_phrases(orig_clean)
    
    if len(wav_keywords) > 0:
        keyword_score = len(wav_keywords & orig_keywords) / len(wav_keywords)
    else:
        keyword_score = 0
    
    # 特殊处理一些常见的变换
    special_matches = [
        ('teamfight tactics', 'tft'),
        ('world of warcraft', 'wow'),
        ('user experience', 'ux'),
        ('game developers conference', 'gdc'),
        ('artificial intelligence', 'ai'),
        ('machine learning', 'ml'),
        ('dragon age', 'dragon age'),
        ('rainbow six siege', 'rainbow six'),
        ('call of duty', 'cod'),
        ('astro bot', 'astrobot'),
    ]
    
    bonus = 0
    for full_term, short_term in special_matches:
        if (full_term in wav_norm and short_term in orig_norm) or \
           (short_term in wav_norm and full_term in orig_norm):
            bonus += 0.2
    
    # 综合评分
    final_score = (base_score * 0.5 + keyword_score * 0.4 + bonus * 0.1)
    
    # 如果有数字匹配，增加分数
    wav_numbers = re.findall(r'\d+', wav_clean)
    orig_numbers = re.findall(r'\d+', orig_clean)
    if wav_numbers and orig_numbers and set(wav_numbers) & set(orig_numbers):
        final_score += 0.1
    
    return min(final_score, 1.0)

def create_manual_mappings():
    """创建一些明确的手动映射"""
    mappings = {
        # 已确认的映射
        "Designing the Dragon Age Combat Wheel.wav": "GDC Vault - UX Summit_ Deep Yet Approachable_ Designing the Combat Wheel in 'Dragon Age_ The Veilguard'",
        "Deep Learning for WoW Armor Fitting.wav": "GDC Vault - Machine Learning Summit_ Fitting Armor Assets in 'World of Warcraft' with Deep Learning",
        "Leveraging LLMs and Multimodal Retrieval in Call of Duty (1).wav": "GDC Vault - Machine Learning Summit_ Enhancing Development with LLMs and Multimodal Retrieval in 'Call of Duty'",
        "Rainbow Six Siege Anti-Cheat_ Machine Learning Stats.wav": "GDC Vault - Machine Learning Summit_ Developing a Stats-Based Anti-Cheat Framework for 'Rainbow Six Siege'",
        "Teamfight Tactics Cyclical Re-engagement Strategy (1).wav": "GDC Vault - Live Service Games Summit_ Welcome Back, Tacticians_ How 'Teamfight Tactics' Supports Returning Players",
        "Empowering Creation_ Eggy Party's UGC Editor Design.wav": "GDC Vault - Behind a Hundred Million Mini-Games_ Why Everyone Loves Creating Games in 'Eggy Party'",
        "Gaming Competitive Intelligence Strategies.wav": "GDC Vault - Beating the Competition_ Competitive Intelligence in Gaming",
        "ASTRO BOT Rapid Creative Gameplay Prototyping.wav": "GDC Vault - Rapid and Creative Gameplay Prototyping in 'ASTRO BOT'",
        "Microtalks About Spreadsheets in Game Design.wav": "GDC Vault - Tools Summit_ A Series of Microtalks About Spreadsheets",
        "The Future of Gaming_ The Next 1,000 Days.wav": "GDC Vault - The Future of Gaming_ The Next 1,000 Days (Presented by GlobalStep)",
        "Serving Players' Needs_ A New Look at What Players Want.wav": "GDC Vault - Serving Players' Needs_ A New Look at What Players Want",
        "AI for Game Ad Transformation.wav": "GDC Vault - How AI Transforms Ad Analysis and Creation for Games (Presented by INCYMO.AI)",
        "Game Studio Principles Case Study.wav": "GDC Vault - Game Studio Principles_ A Case Study",
        "Improving Game Benchmarking with Steam Tags.wav": "GDC Vault - How to Improve Benchmarking Using Steam Tags",
        "GDC Vault_ Leaders Working at the Heart of the Team.wav": "GDC Vault - Leaders Working at the Heart of the Team 2025",
        "World of Warcraft Live Game Learnings.wav": "GDC Vault - Live Service Games Summit_ Live Game Learnings",
        "Game Personalization through Player Telemetry.wav": "GDC Vault - Game Intelligence_ Bringing the Player Voice to the Developers",
        
        # 基于搜索结果添加的新映射
        "Updating RPGs for Modern Audiences_ Metaphor's Design Insights.wav": "GDC Vault - Developing 'Metaphor_ ReFantazio' and the Potential of RPG Command Battle Systems",
        "Tapping into Free-To-Play Mobile Game Potential.wav": "GDC Vault - Live Service Games Summit_ The Untapped Future and Opportunities of Free-To-Play",
        "Decoding Decade-Long Gamer Trends.wav": "GDC Vault - Unlocking Gamer Motivations_ Insights from 1.75+ Million Players Over a Decade",
        "Building Worlds and Characters Through Connection and Humor.wav": "GDC Vault - Game Narrative Summit_ Building Worlds and Characters Through Connection and Humor",
        "Sweet Gets Serious_ Building Candy Crush Allstars.wav": "GDC Vault - Sweet Gets Serious_ Building 'Candy Crush AllStars'",
    }
    return mappings

def main():
    # 设置工作目录
    work_dir = r"D:\GDC\2025"
    os.chdir(work_dir)
    
    # 获取所有文件
    all_files = os.listdir(".")
    
    # 分类文件
    wav_files = sorted([f for f in all_files if f.endswith('.wav')])
    txt_files = [f for f in all_files if f.endswith('.txt') and f.startswith('GDC Vault')]
    mp3_files = [f for f in all_files if f.endswith('.mp3') and f.startswith('GDC Vault')]
    png_files = [f for f in all_files if f.endswith('.png') and f.startswith('GDC Vault')]
    
    # 获取所有原始文件名（去除扩展名）
    original_names = set()
    for f in txt_files + mp3_files + png_files:
        base_name = os.path.splitext(f)[0]
        original_names.add(base_name)
    
    # 为未找到的文件添加一些可能的名称（基于经验和常见模式）
    additional_names = [
        "GDC Vault - Game Narrative Summit_ Building Worlds and Characters Through Connection and Humor",
        "GDC Vault - Unlocking Gamer Motivations_ Insights from 1.75+ Million Players Over a Decade",
        "GDC Vault - Sweet Gets Serious_ Building 'Candy Crush AllStars'",
        "GDC Vault - Live Service Games Summit_ The Untapped Future and Opportunities of Free-To-Play",
        "GDC Vault - Developing 'Metaphor_ ReFantazio' and the Potential of RPG Command Battle Systems",
    ]
    
    for name in additional_names:
        original_names.add(name)
    
    original_names = sorted(list(original_names))
    
    print(f"找到 {len(wav_files)} 个 WAV 文件")
    print(f"找到 {len(original_names)} 个原始文件名（包括添加的）\n")
    
    # 获取手动映射
    manual_mappings = create_manual_mappings()
    
    # 匹配结果
    matches = []
    unmatched = []
    
    # 为每个wav文件找到最佳匹配
    for wav_file in wav_files:
        # 先检查手动映射
        if wav_file in manual_mappings:
            matches.append({
                'old': wav_file,
                'new': manual_mappings[wav_file] + '.wav',
                'score': 1.0,
                'method': 'manual'
            })
            continue
        
        # 自动匹配
        best_match = None
        best_score = 0
        
        for orig_name in original_names:
            score = calculate_match_score(wav_file, orig_name)
            
            if score > best_score:
                best_score = score
                best_match = orig_name
        
        if best_match and best_score > 0.3:  # 降低阈值
            matches.append({
                'old': wav_file,
                'new': best_match + '.wav',
                'score': best_score,
                'method': 'auto'
            })
        else:
            unmatched.append(wav_file)
    
    # 保存匹配结果到文件
    result = {
        'matches': matches,
        'unmatched': unmatched,
        'total_wav': len(wav_files),
        'total_matched': len(matches),
        'total_unmatched': len(unmatched)
    }
    
    with open('wav_rename_preview_v3.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 生成可读的预览文件
    with open('wav_rename_preview_v3.txt', 'w', encoding='utf-8') as f:
        f.write("WAV文件重命名预览 (版本3)\n")
        f.write("=" * 120 + "\n\n")
        
        f.write(f"总计: {len(wav_files)} 个WAV文件\n")
        f.write(f"匹配成功: {len(matches)} 个\n")
        f.write(f"未匹配: {len(unmatched)} 个\n\n")
        
        f.write("匹配结果（按匹配度排序）：\n")
        f.write("-" * 120 + "\n")
        
        # 按匹配度排序
        sorted_matches = sorted(matches, key=lambda x: (-x['score'], x['old']))
        
        for i, match in enumerate(sorted_matches, 1):
            f.write(f"\n{i}. 匹配度: {match['score']:.2f} ({match['method']})\n")
            f.write(f"   原文件: {match['old']}\n")
            f.write(f"   新文件: {match['new']}\n")
        
        if unmatched:
            f.write("\n\n未匹配的文件：\n")
            f.write("-" * 120 + "\n")
            for i, wav in enumerate(unmatched, 1):
                f.write(f"{i}. {wav}\n")
    
    print("预览文件已生成：")
    print("- wav_rename_preview_v3.txt (可读格式)")
    print("- wav_rename_preview_v3.json (JSON格式)")
    print("\n请检查匹配结果，如果满意，运行 execute_rename_v3.py 执行重命名")

if __name__ == "__main__":
    main() 