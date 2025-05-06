import os
import subprocess
import sys
from google import genai
import json

def load_api_key():
    """
    从配置文件中加载Gemini API密钥
    
    Returns:
        str: API密钥，如果未找到则返回None
    """
    try:
        # 从config.json文件加载API密钥
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("gemini_api_key")
        
        return None
    except Exception as e:
        print(f"加载API密钥时出错: {str(e)}")
        return None

def get_audio_summary(audio_path):
    """
    使用Gemini API获取音频文件的中文摘要。
    
    Args:
        audio_path (str): 音频文件的路径
    
    Returns:
        str: 音频内容的中文摘要，如果出错则返回错误信息
    """
    try:
        # 从配置文件加载API密钥
        api_key = load_api_key()
        if not api_key:
            return "错误: 未找到API密钥。请在config.json中配置gemini_api_key。"
        
        # 初始化Gemini客户端
        client = genai.Client(api_key=api_key)
        
        # 上传音频文件
        myfile = client.files.upload(file=audio_path)
        
        # 生成音频内容摘要
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17", 
            contents=["用中文摘要这个音频内容，保留核心的内容，不要包含任何无关的描述，直接生成摘要，不要回到这个问题", myfile]
        )
        
        return response.text
    except Exception as e:
        return f"获取音频摘要时出错: {str(e)}"

def process_videos(directory=".", generate_summary=False):
    """
    处理指定目录中的视频文件：
    1. 将 .ts 文件转换为 .mp4 文件 (如果目标 .mp4 不存在)。
    2. 将 .ts 或 .mp4 文件转换为 .mp3 音频文件 (如果目标 .mp3 不存在)。
    3. 可选地为生成的 .mp3 文件生成中文摘要 (如果目标 .txt 不存在)。

    Args:
        directory (str): 包含视频文件的目录路径。默认为当前目录。
        generate_summary (bool): 是否为转换后的音频生成摘要。默认为False。
    """
    found_videos = False
    processed_bases = set() # 跟踪已处理的基本文件名，防止重复处理

    # 第一轮：优先处理 TS 文件，确保 MP4 转换优先发生
    for filename in sorted(os.listdir(directory)): #排序确保一致性
        base_name, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower == '.ts':
            found_videos = True
            if base_name in processed_bases:
                continue
            processed_bases.add(base_name) # 标记为已处理

            video_path = os.path.join(directory, filename)
            mp4_filename = base_name + ".mp4"
            mp4_path = os.path.join(directory, mp4_filename)
            audio_filename = base_name + ".mp3"
            audio_path = os.path.join(directory, audio_filename)
            summary_filename = base_name + ".txt"
            summary_path = os.path.join(directory, summary_filename)
            png_filename = base_name + ".png"
            png_path = os.path.join(directory, png_filename)

            print(f"发现TS视频文件: {filename}")

            # 1. TS to MP4 Conversion
            if os.path.exists(mp4_path):
                print(f"  跳过转换: MP4文件 '{mp4_filename}' 已存在.")
                video_input_for_audio = mp4_path # 使用现有的 MP4 进行音频提取
                mp4_path_for_keyframe = mp4_path
            else:
                print(f"  开始转换 '{filename}' 为 '{mp4_filename}'...")
                # 尝试使用 stream copy 以提高速度
                convert_command = [
                    'ffmpeg',
                    '-i', video_path,
                    '-c', 'copy', # 尝试直接复制流
                    '-bsf:a', 'aac_adtstoasc', # 通常需要用于 TS -> MP4
                    '-loglevel', 'error',
                    mp4_path
                ]
                try:
                    subprocess.run(convert_command, check=True, capture_output=True, text=True, encoding='utf-8')
                    print(f"  成功转换: '{mp4_filename}'")
                    video_input_for_audio = mp4_path
                    mp4_path_for_keyframe = mp4_path
                except subprocess.CalledProcessError as e:
                    print(f"  警告: 使用 stream copy 转换 TS->MP4 失败，尝试重新编码...", file=sys.stderr)
                    # print(f"    ffmpeg 错误输出:\n{e.stderr}", file=sys.stderr)
                    # 如果 copy 失败，尝试重新编码（可能较慢）
                    convert_command_recode = [
                        'ffmpeg',
                        '-i', video_path,
                        '-c:v', 'libx264', # 或者其他兼容编码器
                        '-c:a', 'aac',     # 或者其他兼容编码器
                        '-loglevel', 'error',
                        mp4_path
                    ]
                    try:
                        subprocess.run(convert_command_recode, check=True, capture_output=True, text=True, encoding='utf-8')
                        print(f"  成功转换 (重新编码): '{mp4_filename}'")
                        video_input_for_audio = mp4_path
                        mp4_path_for_keyframe = mp4_path
                    except Exception as e_recode:
                        print(f"  错误: TS->MP4 转换失败: '{filename}'", file=sys.stderr)
                        # print(f"    ffmpeg 错误输出:\n{e_recode.stderr if isinstance(e_recode, subprocess.CalledProcessError) else e_recode}", file=sys.stderr)
                        video_input_for_audio = video_path # 转换失败，回退到使用原始 TS 提取音频
                        mp4_path_for_keyframe = None # 标记 MP4 不可用
                    else:
                        mp4_path_for_keyframe = mp4_path # 标记 MP4 可用

            # --- 新增：提取关键帧 (需要 MP4 文件) ---
            if mp4_path_for_keyframe: # 仅当 MP4 文件存在或转换成功时执行
                if os.path.exists(png_path):
                    print(f"  跳过: 关键帧文件 '{png_filename}' 已存在.")
                else:
                    print(f"  开始从 '{os.path.basename(mp4_path_for_keyframe)}' 提取关键帧为 '{png_filename}'...")
                    keyframe_command = [
                        'ffmpeg',
                        '-ss', '180',         # 修改：尝试从第 180 秒开始查找
                        '-i', mp4_path_for_keyframe,
                        '-vframes', '1',
                        '-q:v', '2',         # PNG 质量
                        '-loglevel', 'error',
                        png_path
                    ]
                    try:
                        subprocess.run(keyframe_command, check=True, capture_output=True, text=True, encoding='utf-8')
                        print(f"  成功提取关键帧: '{png_filename}'")
                    except FileNotFoundError:
                         # ffmpeg 未找到的错误已在下面处理，这里避免重复打印
                         pass
                    except subprocess.CalledProcessError as e:
                        print(f"  错误: 从 '{os.path.basename(mp4_path_for_keyframe)}' 提取关键帧失败", file=sys.stderr)
                        # print(f"    ffmpeg 错误输出:\n{e.stderr}", file=sys.stderr)
                    except Exception as e:
                        print(f"  提取关键帧时发生未知错误: {e}", file=sys.stderr)
            elif not os.path.exists(png_path): # 如果 MP4 不可用且 PNG 不存在
                 print(f"  跳过关键帧提取: 无法生成或找到 MP4 文件 '{mp4_filename}'.")
            # --- 结束：提取关键帧 ---

            # 2. Video (TS or resulting MP4) to MP3 Conversion
            if os.path.exists(audio_path):
                print(f"  跳过转换: 音频文件 '{audio_filename}' 已存在.")
                # 检查是否需要生成摘要
                if generate_summary and not os.path.exists(summary_path):
                    print(f"  正在为现有音频文件 '{audio_filename}' 生成摘要...")
                    summary = get_audio_summary(audio_path)
                    print(f"  音频摘要:\n{summary}\n")
                    try:
                        with open(summary_path, 'w', encoding='utf-8') as f:
                            f.write(summary)
                        print(f"  已将摘要保存到 '{summary_filename}'")
                    except Exception as e:
                        print(f"  保存摘要到文件时出错: {e}", file=sys.stderr)
                elif generate_summary and os.path.exists(summary_path):
                     print(f"  跳过: 摘要文件 '{summary_filename}' 已存在.")

            else:
                print(f"  开始从 '{os.path.basename(video_input_for_audio)}' 提取音频为 '{audio_filename}'...")
                audio_command = [
                    'ffmpeg',
                    '-i', video_input_for_audio,
                    '-vn',
                    '-q:a', '2',
                    '-loglevel', 'error',
                    audio_path
                ]
                try:
                    subprocess.run(audio_command, check=True, capture_output=True, text=True, encoding='utf-8')
                    print(f"  成功提取音频: '{audio_filename}'")
                    # 如果需要生成摘要
                    if generate_summary:
                        if os.path.exists(summary_path):
                            print(f"  跳过: 摘要文件 '{summary_filename}' 已存在.")
                        else:
                            print(f"  正在为新提取的音频文件 '{audio_filename}' 生成摘要...")
                            summary = get_audio_summary(audio_path)
                            print(f"  音频摘要:\n{summary}\n")
                            try:
                                with open(summary_path, 'w', encoding='utf-8') as f:
                                    f.write(summary)
                                print(f"  已将摘要保存到 '{summary_filename}'")
                            except Exception as e:
                                print(f"  保存摘要到文件时出错: {e}", file=sys.stderr)

                except FileNotFoundError:
                    print("错误: 未找到 ffmpeg。请确保已安装 ffmpeg 并将其添加到了系统 PATH。", file=sys.stderr)
                    sys.exit(1) # ffmpeg 未找到是致命错误
                except subprocess.CalledProcessError as e:
                    print(f"  错误: 音频提取失败: '{os.path.basename(video_input_for_audio)}'", file=sys.stderr)
                    # print(f"    ffmpeg 错误输出:\n{e.stderr}", file=sys.stderr)
                except Exception as e:
                     print(f"  音频提取或摘要生成时发生未知错误: {e}", file=sys.stderr)

    # 第二轮：处理剩余的 MP4 文件 (那些没有对应 TS 文件或 TS 处理失败的)
    for filename in sorted(os.listdir(directory)):
        base_name, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower == '.mp4':
            # 如果这个 MP4 是由 TS 文件生成的，它已经在上一轮被处理过了
            if base_name in processed_bases:
                continue

            # 检查是否存在同名的 TS 文件，如果存在，则假设它已在上一轮处理
            ts_filename = base_name + ".ts"
            ts_path = os.path.join(directory, ts_filename)
            if os.path.exists(ts_path):
                # 理论上不应该到这里，因为 processed_bases 会捕获它，但作为安全措施
                continue

            found_videos = True
            processed_bases.add(base_name) # 标记为已处理

            video_path = os.path.join(directory, filename)
            audio_filename = base_name + ".mp3"
            audio_path = os.path.join(directory, audio_filename)
            summary_filename = base_name + ".txt"
            summary_path = os.path.join(directory, summary_filename)
            png_filename = base_name + ".png"
            png_path = os.path.join(directory, png_filename)

            print(f"发现MP4视频文件: {filename}")

            # --- 新增：提取关键帧 ---
            if os.path.exists(png_path):
                print(f"  跳过: 关键帧文件 '{png_filename}' 已存在.")
            else:
                print(f"  开始从 '{filename}' 提取关键帧为 '{png_filename}'...")
                keyframe_command = [
                    'ffmpeg',
                    '-ss', '180',        # 修改：尝试从第 180 秒开始查找
                    '-i', video_path, # video_path 就是 MP4 路径
                    '-vframes', '1',
                    '-q:v', '2',         # PNG 质量
                    '-loglevel', 'error',
                    png_path
                ]
                try:
                    subprocess.run(keyframe_command, check=True, capture_output=True, text=True, encoding='utf-8')
                    print(f"  成功提取关键帧: '{png_filename}'")
                except FileNotFoundError:
                     # ffmpeg 未找到的错误已在下面处理，这里避免重复打印
                     pass
                except subprocess.CalledProcessError as e:
                    print(f"  错误: 从 '{filename}' 提取关键帧失败", file=sys.stderr)
                    # print(f"    ffmpeg 错误输出:\n{e.stderr}", file=sys.stderr)
                except Exception as e:
                    print(f"  提取关键帧时发生未知错误: {e}", file=sys.stderr)
            # --- 结束：提取关键帧 ---

            # MP4 to MP3 Conversion
            if os.path.exists(audio_path):
                print(f"  跳过: 音频文件 '{audio_filename}' 已存在.")
                # 检查是否需要生成摘要
                if generate_summary and not os.path.exists(summary_path):
                    print(f"  正在为现有音频文件 '{audio_filename}' 生成摘要...")
                    summary = get_audio_summary(audio_path)
                    print(f"  音频摘要:\n{summary}\n")
                    try:
                        with open(summary_path, 'w', encoding='utf-8') as f:
                            f.write(summary)
                        print(f"  已将摘要保存到 '{summary_filename}'")
                    except Exception as e:
                        print(f"  保存摘要到文件时出错: {e}", file=sys.stderr)
                elif generate_summary and os.path.exists(summary_path):
                     print(f"  跳过: 摘要文件 '{summary_filename}' 已存在.")
            else:
                print(f"  开始从 '{filename}' 提取音频为 '{audio_filename}'...")
                audio_command = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vn',
                    '-q:a', '2',
                    '-loglevel', 'error',
                    audio_path
                ]
                try:
                    subprocess.run(audio_command, check=True, capture_output=True, text=True, encoding='utf-8')
                    print(f"  成功提取音频: '{audio_filename}'")
                    # 如果需要生成摘要
                    if generate_summary:
                        if os.path.exists(summary_path):
                             print(f"  跳过: 摘要文件 '{summary_filename}' 已存在.")
                        else:
                            print(f"  正在为新提取的音频文件 '{audio_filename}' 生成摘要...")
                            summary = get_audio_summary(audio_path)
                            print(f"  音频摘要:\n{summary}\n")
                            try:
                                with open(summary_path, 'w', encoding='utf-8') as f:
                                    f.write(summary)
                                print(f"  已将摘要保存到 '{summary_filename}'")
                            except Exception as e:
                                print(f"  保存摘要到文件时出错: {e}", file=sys.stderr)
                except FileNotFoundError:
                    print("错误: 未找到 ffmpeg。请确保已安装 ffmpeg 并将其添加到了系统 PATH。", file=sys.stderr)
                    sys.exit(1) # ffmpeg 未找到是致命错误
                except subprocess.CalledProcessError as e:
                    print(f"  错误: 音频提取失败: '{filename}'", file=sys.stderr)
                    # print(f"    ffmpeg 错误输出:\n{e.stderr}", file=sys.stderr)
                except Exception as e:
                     print(f"  音频提取或摘要生成时发生未知错误: {e}", file=sys.stderr)


    if not found_videos:
        print(f"在目录 '{os.path.abspath(directory)}' 中未找到 .ts 或 .mp4 文件。")

if __name__ == "__main__":
    target_directory = "." # 默认使用当前目录
    # 如果需要指定目录，可以取消下面这行注释并修改路径
    target_directory = "./2024"

    print(f"开始在目录 '{os.path.abspath(target_directory)}' 中查找视频文件...")
    
    # 检查API密钥是否可用
    generate_summary = load_api_key() is not None
    if generate_summary:
        print("检测到API密钥配置，将为音频生成摘要。")
    else:
        print("未检测到API密钥配置，将跳过摘要生成。请在config.json中配置gemini_api_key。")

    process_videos(target_directory, generate_summary)
    print("处理完成。") 
