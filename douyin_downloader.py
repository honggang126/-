from DrissionPage import ChromiumPage
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import re
import time
import queue
from datetime import datetime

dp = ChromiumPage()
dp.listen.start('aweme/v1/web/aweme/post/')
dp.get('https://www.douyin.com/user/MS4wLjABAAAAvj3tkImETfH6fkwlhWI5Iu951NABx0wMYfVV8UivpnO-taha4O9Z-JJ6t3AgduFI?from_tab_name=main')

# 创建视频目录
video_dir = os.path.join(os.getcwd(), 'video')
if not os.path.exists(video_dir):
    try:
        os.makedirs(video_dir)
    except Exception as e:
        print(f"创建视频目录失败: {str(e)}")
        exit()

download_count = 0
video_queue = queue.Queue()
total_size = 0
start_time = datetime.now()

def download_worker():
    global download_count, total_size
    while True:
        video = video_queue.get()
        if video is None:  # 终止信号
            break
            
        title = video['desc']
        title = re.sub(r'[\/:*?"<>|]', '', title)
        video_url = video['video']['play_addr']['url_list'][0]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'cookie': 'odin_tt=8529647681725897765859056702770603312878270037652679023270071408173845397424n',
            'referer':'http://www.douyin.com'
        }
        
        for retry in range(3):
            try:
                start = time.time()
                response = requests.get(url=video_url, headers=headers, timeout=10, stream=True)
                file_size = int(response.headers.get('content-length', 0))
                video_content = response.content
                
                with open(f'video\\{title}.mp4', mode='wb') as f:
                    f.write(video_content)
                
                download_count += 1
                total_size += file_size
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = (total_size / 1024 / 1024) / elapsed if elapsed > 0 else 0
                
                print(f"第{download_count}条视频下载完成: {title} | 大小: {file_size/1024/1024:.2f}MB | 平均速度: {speed:.2f}MB/s")
                break
            except Exception as e:
                print(f"第{retry+1}次尝试下载失败 {title}: {str(e)}")
                time.sleep(2)
        
        video_queue.task_done()

# 启动10个下载线程
with ThreadPoolExecutor(max_workers=10) as executor:
    # 启动下载线程
    futures = [executor.submit(download_worker) for _ in range(10)]
    
    try:
        for page in range(1, 20):  # 增加滚动页数
            print(f'正在解析第{page}页的内容，稍等片刻！')
            dp.run_js('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)  # 减少等待时间
            
            resp = dp.listen.wait()
            if resp and hasattr(resp.response, 'body'):
                josp_data = resp.response.body
                if 'aweme_list' in josp_data:
                    for video in josp_data['aweme_list']:
                        video_queue.put(video)
                else:
                    print("未获取到视频列表数据")
            else:
                print("响应数据异常")
                
    finally:
        # 添加终止信号
        for _ in range(10):
            video_queue.put(None)
        executor.shutdown()
    