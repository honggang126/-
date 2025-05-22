import os
import time
import requests
import logging
from urllib.parse import quote
from DrissionPage import ChromiumPage
from DrissionPage.common import Actions

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='douyin_downloader.log'
)
logger = logging.getLogger(__name__)

class DouyinDownloader:
    def __init__(self, save_dir="e:\\抖音视频下载00"):
        self.page = ChromiumPage()
        self.ac = Actions(self.page)
        self.save_dir = save_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.douyin.com/'
        }
        
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            logger.info(f"创建保存目录: {save_dir}")

    def get_video_list(self, keyword, count=20):
        """获取视频列表"""
        encoded_keyword = quote(keyword)
        url = f'https://www.douyin.com/discover/search/{encoded_keyword}?type=video'
        
        logger.info(f"开始获取视频列表，关键词: {keyword}, 目标数量: {count}")
        self.page.get(url)
        
        # 等待页面加载
        time.sleep(5)  # 增加等待时间
        
        video_list = []
        scroll_attempts = 0
        max_attempts = 20
        
        while len(video_list) < count and scroll_attempts < max_attempts:
            # 尝试多种选择器
            video_elements = self.page.eles('css:li.SWZLHMKk.SEbmeLLH') or \
                           self.page.eles('css:li[class*="SWZLHMKk"]') or \
                           self.page.eles('css:li[class*="SEbmeLLH"]')
            
            if video_elements and len(video_elements) > len(video_list):
                new_videos = video_elements[len(video_list):count]
                video_list.extend(new_videos)
                logger.info(f"已获取 {len(video_list)}/{count} 个视频")
            
            # 滚动页面
            self.ac.scroll(delta_y=1000)  # 增加滚动距离
            time.sleep(2)  # 增加滚动后等待时间
            scroll_attempts += 1
        
        return video_list[:count]

    def get_video_url(self, video_element, max_retries=3):
        """获取单个视频的真实下载地址"""
        tab = None
        try:
            # 获取视频链接并打开新标签
            link = video_element.ele('css:a[href*="/video/"]').link
            if not link:
                logger.warning("未找到视频链接元素")
                return None, None
                
            tab = self.page.new_tab(link)
            tab.wait.load_start()
            
            # 检查是否有登录弹窗
            if tab.ele('css:.dy-account-close'):
                tab.ele('css:.dy-account-close').click()
                time.sleep(1)
            
            # 启动监听
            tab.listen.start("v26-web.douyinvod.com")
            
            # 等待获取视频数据
            data = tab.listen.wait(timeout=15)
            
            if data:
                return tab, data.url
            else:
                logger.warning("未获取到视频数据")
                return None, None
            
        except Exception as e:
            logger.error(f"获取视频URL失败: {str(e)}")
            if tab:
                tab.close()
            return None, None

    def download_video(self, video_url, video_title, max_retries=3):
        """下载视频"""
        # 清理文件名中的非法字符
        safe_title = "".join(c for c in video_title if c not in r'\/:*?"<>|')
        save_path = os.path.join(self.save_dir, f"{safe_title}.mp4")
        
        # 如果文件已存在且大小不为0，则跳过下载
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            logger.info(f"文件已存在: {save_path}")
            return save_path
        
        for attempt in range(max_retries):
            try:
                logger.info(f"开始下载视频: {video_title}")
                response = requests.get(video_url, headers=self.headers, stream=True, timeout=30)
                response.raise_for_status()
                
                # 获取文件大小
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024
                bytes_written = 0
                
                with open(save_path, 'wb') as f:
                    for data in response.iter_content(block_size):
                        bytes_written += len(data)
                        f.write(data)
                        # 显示下载进度
                        if total_size > 0:
                            progress = (bytes_written / total_size) * 100
                            print(f"\r下载进度: {progress:.2f}%", end="")
                
                if total_size > 0:
                    print()  # 换行
                    
                logger.info(f"视频下载成功: {save_path}")
                return save_path
                
            except Exception as e:
                logger.error(f"尝试 {attempt+1}/{max_retries}: 下载视频失败: {str(e)}")
                if os.path.exists(save_path):
                    os.remove(save_path)  # 删除不完整文件
                time.sleep(3)
        
        logger.error(f"下载视频失败: {video_title}")
        return None

    def run(self, keyword, count=20):
        """运行下载器"""
        try:
            logger.info("=" * 50)
            logger.info(f"开始抖音视频下载任务，关键词: {keyword}, 目标数量: {count}")
            
            # 获取视频列表
            video_list = self.get_video_list(keyword, count)
            print(f"成功获取 {len(video_list)} 个视频")
            
            # 下载每个视频
            for i, video in enumerate(video_list, 1):
                print(f"\n正在下载第 {i}/{len(video_list)} 个视频")
                tab, video_url = self.get_video_url(video)
                
                if not video_url:
                    print("获取视频链接失败，跳过")
                    continue
                
                video_title = tab.title
                save_path = self.download_video(video_url, video_title)
                
                if save_path:
                    print(f"视频已保存到: {save_path}")
                else:
                    print("视频下载失败")
                
                # 关闭标签页
                if tab:
                    tab.close()
                time.sleep(1)  # 避免过快请求
            
            logger.info(f"下载任务完成，共下载 {len(video_list)} 个视频")
            
        except Exception as e:
            logger.critical(f"下载器运行失败: {str(e)}", exc_info=True)
            print(f"程序运行出错: {str(e)}")
        finally:
            # 关闭浏览器
            self.page.quit()
            logger.info("浏览器已关闭")

if __name__ == "__main__":
    downloader = DouyinDownloader()
    downloader.run("鸭脖", 20)