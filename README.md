import streamlit as st
import os
import random
import time
from pathlib import Path
import pygame
from datetime import datetime
import base64

# 页面配置
st.set_page_config(
    page_title="Streamlit音乐播放器",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 初始化音频系统
def init_audio():
    try:
        pygame.mixer.init()
        return True
    except:
        st.warning("音频系统初始化失败，请确保已安装pygame库")
        return False

# 自定义CSS样式
def local_css():
    st.markdown("""
    <style>
    /* 主容器样式 */
    .stApp {
        background-color: #000000;
        color: white;
    }
    
    /* 头部样式 */
    .header {
        text-align: center;
        padding: 20px 0;
        margin-bottom: 30px;
        border-bottom: 1px solid #333;
    }
    
    .app-title {
        font-size: 2.8rem;
        font-weight: bold;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    
    .app-subtitle {
        font-size: 1.2rem;
        color: #888;
        margin-bottom: 20px;
    }
    
    /* 播放器容器 */
    .player-container {
        background: rgba(20, 20, 20, 0.9);
        border-radius: 20px;
        padding: 40px;
        margin: 30px auto;
        max-width: 900px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.7);
        border: 1px solid #333;
    }
    
    /* 专辑封面样式 */
    .album-cover-container {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .album-cover {
        width: 280px;
        height: 280px;
        border-radius: 15px;
        object-fit: cover;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.8);
        margin: 0 auto;
        border: 3px solid #444;
    }
    
    /* 歌曲信息样式 */
    .song-info {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .song-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 10px;
        letter-spacing: 1px;
    }
    
    .artist-name {
        font-size: 1.5rem;
        color: #cccccc;
        margin-bottom: 8px;
    }
    
    .duration {
        font-size: 1.3rem;
        color: #888888;
        font-weight: 300;
    }
    
    /* 控制按钮样式 */
    .controls-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 30px;
        margin: 30px 0;
    }
    
    .control-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        color: white;
        font-size: 1.5rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.4);
    }
    
    .control-btn:hover {
        transform: scale(1.1);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.6);
    }
    
    .play-pause-btn {
        width: 80px;
        height: 80px;
        font-size: 2rem;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    /* 进度条样式 */
    .progress-container {
        margin: 30px 0;
    }
    
    .progress-label {
        display: flex;
        justify-content: space-between;
        color: #aaa;
        margin-bottom: 10px;
        font-size: 1.1rem;
    }
    
    .stSlider > div {
        height: 8px;
    }
    
    /* 歌曲列表样式 */
    .song-list-container {
        background: rgba(30, 30, 30, 0.9);
        border-radius: 15px;
        padding: 25px;
        margin-top: 40px;
    }
    
    .song-list-title {
        font-size: 1.8rem;
        color: #fff;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #444;
    }
    
    .song-item {
        padding: 15px 20px;
        margin: 8px 0;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 4px solid transparent;
    }
    
    .song-item:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateX(5px);
        border-left: 4px solid #667eea;
    }
    
    .song-item.active {
        background: linear-gradient(90deg, rgba(102, 126, 234, 0.2
