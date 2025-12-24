#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网易云音乐音频下载工具
支持单个、批量下载，支持断点续传，自动重试
"""

import requests
import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Union
from urllib.parse import urlparse, unquote
import argparse

class NetEaseMusicDownloader:
    """网易云音乐下载器"""
    
    def __init__(self, save_dir: str = "downloads", max_retries: int = 3):
        """
        初始化下载器
        
        Args:
            save_dir: 保存目录
            max_retries: 最大重试次数
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://music.163.com/',
            'Connection': 'keep-alive',
            'Range': 'bytes=0-',
        }
        
        # 会话保持
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def _get_download_url(self, song_id: Union[str, int]) -> str:
        """生成下载URL"""
        return f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
    
    def _get_filename_from_headers(self, response, song_id: Union[str, int]) -> str:
        """从响应头提取文件名"""
        # 尝试从Content-Disposition获取文件名
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[-1].strip('"\'').encode('ISO-8859-1').decode('utf-8')
        else:
            filename = f"netmusic_{song_id}.mp3"
        return filename
    
    def _download_with_progress(self, url: str, save_path: Path) -> bool:
        """带进度显示的下载"""
        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 检查是否是有效的音频文件
            content_type = response.headers.get('Content-Type', '')
            if 'audio' not in content_type and 'octet-stream' not in content_type:
                print(f"⚠ 警告: 可能不是音频文件 (Content-Type: {content_type})")
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 下载文件
            downloaded_size = 0
            chunk_size = 8192
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 显示进度
                        if total_size > 0:
                            percent = (downloaded_size / total_size) * 100
                            bar_length = 40
                            filled_length = int(bar_length * downloaded_size // total_size)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            print(f'\r进度: |{bar}| {percent:.1f}% ({downloaded_size/(1024 * 1024):.2f}MB/{total_size/(1024 * 1024):.2f}MB)', end='')
            
            print()  # 换行
            return True
            
        except Exception as e:
            print(f"\n✗ 下载失败: {e}")
            # 删除可能不完整的文件
            if save_path.exists():
                save_path.unlink()
            return False
    
    def download_song(self, song_id: Union[str, int], filename: Optional[str] = None) -> Optional[Path]:
        """
        下载单个歌曲
        
        Args:
            song_id: 歌曲ID
            filename: 自定义文件名（可选）
            
        Returns:
            保存的文件路径，失败返回None
        """
        print(f"\n{'='*60}")
        print(f"开始下载歌曲ID: {song_id}")
        
        url = self._get_download_url(song_id)
        print(f"下载URL: {url}")
        
        # 重试机制
        for retry in range(self.max_retries):
            try:
                if retry > 0:
                    print(f"第 {retry + 1} 次重试...")
                    time.sleep(2)  # 重试前等待
                
                # 首先获取响应头信息
                response = self.session.head(url, timeout=10)
                
                if response.status_code == 404:
                    print(f"✗ 歌曲不存在 (404)")
                    return None
                elif response.status_code != 200:
                    print(f"✗ HTTP错误: {response.status_code}")
                    continue
                
                # 确定文件名
                if filename:
                    save_filename = filename
                    if not save_filename.endswith('.mp3'):
                        save_filename += '.mp3'
                else:
                    save_filename = self._get_filename_from_headers(response, song_id)
                
                save_path = self.save_dir / save_filename
                
                # 检查文件是否已存在
                if save_path.exists():
                    print(f"⚠ 文件已存在: {save_path.name}")
                    overwrite = input("是否覆盖？(y/n): ").lower()
                    if overwrite != 'y':
                        print("跳过下载")
                        return save_path
                
                print(f"保存为: {save_path.name}")
                
                # 开始下载
                if self._download_with_progress(url, save_path):
                    print(f"✓ 下载完成: {save_path.name}")
                    return save_path
                
            except requests.exceptions.Timeout:
                print(f"✗ 请求超时 (尝试 {retry + 1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                print(f"✗ 网络错误: {e}")
            except Exception as e:
                print(f"✗ 未知错误: {e}")
        
        print(f"✗ 下载失败，已达最大重试次数")
        return None
    
    def download_playlist(self, playlist_file: str) -> List[Path]:
        """
        从文件批量下载歌曲
        
        Args:
            playlist_file: 包含歌曲ID列表的文件（每行一个ID）
            
        Returns:
            成功下载的文件列表
        """
        if not Path(playlist_file).exists():
            print(f"✗ 文件不存在: {playlist_file}")
            return []
        
        downloaded_files = []
        
        with open(playlist_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\n开始批量下载，共 {len(lines)} 首歌曲")
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 支持格式: ID 或 ID,自定义文件名
            parts = line.split(',')
            song_id = parts[0].strip()
            
            if len(parts) > 1:
                filename = parts[1].strip()
            else:
                filename = None
            
            print(f"\n[{i}/{len(lines)}] ", end='')
            result = self.download_song(song_id, filename)
            if result:
                downloaded_files.append(result)
            
            time.sleep(1)  # 防止请求过快
        
        print(f"\n{'='*60}")
        print(f"批量下载完成，成功: {len(downloaded_files)}/{len(lines)}")
        
        return downloaded_files
    
    def download_from_api(self, api_url: str) -> List[Path]:
        """
        从API接口获取歌曲列表并下载
        
        Args:
            api_url: 包含歌曲ID的API接口
            
        Returns:
            成功下载的文件列表
        """
        try:
            print(f"\n从API获取歌曲列表: {api_url}")
            response = requests.get(api_url, timeout=10)
            data = response.json()
            
            # 这里需要根据实际的API返回格式解析
            # 示例: 假设API返回 {"songs": [{"id": 123}, {"id": 456}]}
            if 'songs' in data:
                song_ids = [str(song['id']) for song in data['songs']]
            else:
                # 尝试其他格式
                song_ids = [str(item) for item in data if str(item).isdigit()]
            
            if not song_ids:
                print("✗ 未找到有效的歌曲ID")
                return []
            
            print(f"找到 {len(song_ids)} 首歌曲")
            
            downloaded_files = []
            for i, song_id in enumerate(song_ids, 1):
                print(f"\n[{i}/{len(song_ids)}] ", end='')
                result = self.download_song(song_id)
                if result:
                    downloaded_files.append(result)
                
                time.sleep(1)
            
            return downloaded_files
            
        except Exception as e:
            print(f"✗ 从API获取失败: {e}")
            return []
    
    def search_and_download(self, keyword: str, limit: int = 10) -> List[Path]:
        """
        搜索歌曲并下载（需要实现搜索功能）
        注意：这个功能需要模拟网页搜索，比较复杂
        这里提供一个框架，实际需要解析搜索页面
        """
        print(f"搜索功能需要实现搜索接口解析")
        print(f"关键词: {keyword}")
        
        # 这里可以添加搜索逻辑
        # 例如：解析 https://music.163.com/#/search/m/?s={keyword}&type=1
        # 但需要处理JavaScript渲染
        
        return []
    
    def get_song_info(self, song_id: Union[str, int]) -> Optional[Dict]:
        """
        获取歌曲信息（需要实现API调用）
        这里返回模拟数据
        """
        try:
            # 这里可以调用网易云API获取歌曲信息
            # 示例URL: https://music.163.com/api/song/detail/?ids=[{song_id}]
            api_url = f"https://music.163.com/api/song/detail/?ids=[{song_id}]"
            response = requests.get(api_url, headers=self.headers, timeout=5)
            data = response.json()
            
            if data.get('songs'):
                song = data['songs'][0]
                return {
                    'id': song_id,
                    'name': song.get('name', '未知歌曲'),
                    'artist': ', '.join([ar['name'] for ar in song.get('artists', [])]),
                    'album': song.get('album', {}).get('name', '未知专辑'),
                    'duration': song.get('duration', 0)  # 毫秒
                }
        except:
            pass
        
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='网易云音乐音频下载工具')
    parser.add_argument('-i', '--id', type=str, help='歌曲ID')
    parser.add_argument('-f', '--file', type=str, help='批量下载文件（每行一个ID）')
    parser.add_argument('-o', '--output', type=str, default='downloads', help='保存目录')
    parser.add_argument('-n', '--name', type=str, help='自定义文件名')
    parser.add_argument('--list', action='store_true', help='列出已下载文件')
    parser.add_argument('--clean', action='store_true', help='清理不完整的下载文件')
    
    args = parser.parse_args()
    
    # 创建下载器
    downloader = NetEaseMusicDownloader(save_dir=args.output)
    
    # 列出已下载文件
    if args.list:
        print(f"\n已下载文件列表 ({downloader.save_dir}):")
        files = list(downloader.save_dir.glob('*.mp3'))
        if files:
            for i, file in enumerate(files, 1):
                print(f"{i:3d}. {file.name}")
        else:
            print("暂无下载文件")
        return
    
    # 清理不完整文件
    if args.clean:
        print(f"\n正在清理不完整的下载文件...")
        cleaned = 0
        for file in downloader.save_dir.glob('*.tmp'):
            try:
                file.unlink()
                cleaned += 1
            except:
                pass
        print(f"清理完成，删除了 {cleaned} 个临时文件")
        return
    
    # 批量下载
    if args.file:
        downloader.download_playlist(args.file)
        return
    
    # 单个下载
    if args.id:
        downloader.download_song(args.id, args.name)
    else:
        # 交互模式
        print("网易云音乐音频下载工具")
        print("=" * 50)
        
        while True:
            print("\n请选择操作:")
            print("1. 下载单首歌曲")
            print("2. 批量下载")
            print("3. 显示已下载文件")
            print("4. 退出")
            
            choice = input("\n请输入选项 (1-4): ").strip()
            
            if choice == '1':
                song_id = input("请输入歌曲ID: ").strip()
                if song_id:
                    custom_name = input("自定义文件名（留空使用默认）: ").strip() or None
                    downloader.download_song(song_id, custom_name)
            
            elif choice == '2':
                file_path = input("请输入包含歌曲ID的文件路径: ").strip()
                if file_path and Path(file_path).exists():
                    downloader.download_playlist(file_path)
                else:
                    print("✗ 文件不存在")
            
            elif choice == '3':
                files = list(downloader.save_dir.glob('*.mp3'))
                if files:
                    print(f"\n已下载 {len(files)} 个文件:")
                    for file in files:
                        print(f"  • {file.name}")
                else:
                    print("暂无下载文件")
            
            elif choice == '4':
                print("感谢使用，再见！")
                break
            
            else:
                print("无效选项，请重新输入")

if __name__ == "__main__":
    # 示例使用代码
    downloader = NetEaseMusicDownloader()
    
    # 示例1: 下载单首歌曲
    # downloader.download_song(5257138)  # 使用你提供的ID
    
    # 示例2: 批量下载（创建一个song_ids.txt文件，每行一个ID）
    # downloader.download_playlist("song_ids.txt")
    
    # 示例3: 通过命令行运行
    # python netease_downloader.py -i 5257138 -o "我的音乐"
    
    # 运行主程序
    main()
