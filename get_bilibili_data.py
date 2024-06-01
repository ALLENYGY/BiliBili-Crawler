import requests
import qrcode
import os
import re
from time import sleep
import xml.etree.ElementTree as ET
import pandas as pd
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
}

# Set up the API endpoint
url = 'https://api.bilibili.com/x/web-interface/view/detail'

# Define the parameters
params = {
    'bvid': 'BV117411r7R1'
}

def update_headers_with_cookies(HEADERS):
    print("Ready to scan the code to get cookies...")
    url="https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    response = requests.get(url, headers=HEADERS)
    qrcode_key=response.json()['data']['qrcode_key']
    qr_url=response.json()['data']['url']
    img=qrcode.make(qr_url)
    img.show()
    pass_url="https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key="+qrcode_key
    # Close the window after scanning the code successfully
    response=requests.get(pass_url, headers=HEADERS)
    while response.json()['data']['message']=='未扫码':
        response = requests.get(pass_url, headers=HEADERS)
        print(response.json())
        sleep(3)
    img.close()
    res=response.json()['data']['url']
    match = re.search(r'SESSDATA(.+?)&', res)
    cookies=None
    if match:
        cookies=match.group()
        HEADERS['cookie']=cookies
        return HEADERS
    else:
        print("Get cookies failed!")
        return None

def get_video_info(bvid):
    params['bvid'] = bvid
    response = requests.get(url, params=params, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Filter the response to get the video information
def filter_video_info(video_info):
    if video_info:
        data = video_info['data']
        video_infos = {
            "标题": data['View']['title'],                # title	str	视频标题
            "视频图片": data['View']['pic'],               # pic	str	视频封面         
            "播放量": data['View']['stat']['view'],         # view num	播放数
            "弹幕量": data['View']['stat']['danmaku'],      # danmaku num	弹幕数
            "评论数": data['View']['stat']['reply'],        # repl num	评论数	
            "收藏人数": data['View']['stat']['favorite'],   # favorit num	收藏数	
            "投硬币枚数": data['View']['stat']['coin'],     # coin num	投币数	
            "分享数": data['View']['stat']['share'],       # share num	分享数	
            "获赞数": data['View']['stat']['like'],        # like	num	获赞数	
            "当前排名": data['View']['stat']['now_rank'],   # now_rank	num	当前排名
            "历史最高排行": data['View']['stat']['his_rank'], # his_rank	num	历史最高排行
            "视频作者": data['View']['owner']['name'],     # name	str	作者名
            "视频评分": data['View']['stat']['evaluation']  # evaluation	str	视频评分
        }
        return video_infos
    else:
        return None

def get_video_data(bvid):
    # Get the video information
    print("Begin to crawl video information...")
    video_info = get_video_info(bvid)
    video_infos = filter_video_info(video_info)
    print("Video information has been crawled successfully!")

    # export the video information to a file
    # with open("video_info.txt", "w", encoding="utf-8") as fp:
    #     for key, value in video_infos.items():
    #         fp.write(key + ": " + str(value) + "\n")
    # Create a folder to store the video information
    # bvid is the name of the folder
    # export the video information to a json file
    filepath=os.path.join(bvid,"video_info.json")
    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(video_infos, fp, ensure_ascii=False)
    return video_infos


def get_video_comment(bid):
    str = f"https://www.bilibili.com/video/{bid}"
    aid_ = f"https://api.bilibili.com/x/web-interface/view?bvid={bid}"
    tmp_data = requests.get(aid_, headers=HEADERS).json()
    aid = tmp_data['data']['aid']
    comment = []
    like = []
    pre_comment_length = 0
    i = 0
    while True:
        url = f"https://api.bilibili.com/x/v2/reply/main?csrf=40a227fcf12c380d7d3c81af2cd8c5e8&mode=3&next={i}" \
            f"&oid={aid}&plat=1&type=1"
        try:
            responses = requests.get(url=url.format(i), headers=HEADERS).json()
            i += 1
            for content in responses["data"]["replies"]:
                comment.append(content["content"]["message"])
                like.append(content['like'])
            print("Search %d Comments" % (len(comment)))
            if len(comment) == pre_comment_length:
                print("Quit Crawling Comments!")
                break
            else:
                pre_comment_length = len(comment)
        except Exception as e:
            print(e)
            break
    # Combine the comment and like use dataframe
    comment_like = pd.DataFrame({"comment": comment, "like": like})
    # Export xlsx file
    filepath=os.path.join(bvid,"comment.xlsx")
    comment_like.to_excel(filepath, index=False)
    print("Comment has been crawled successfully!")
    return comment

def get_cid(bvid):
    url="https://api.bilibili.com/x/player/pagelist?bvid="+bvid
    response = requests.get(url, headers=HEADERS)
    return response.json()['data'][0]['cid']

def get_video_dm(cid):
    print("Begin to crawl danmu...")
    cid = str(cid)
    dm_url = f"https://comment.bilibili.com/{cid}.xml"
    response = requests.get(dm_url, headers=HEADERS)
    # export to xml file
    # with open("danmu.xml", "w", encoding="utf-8") as fp:
    #     fp.write(response.text)
    danmu=parse_xml(response.content)
    print("Danmu has been crawled successfully!")
    return danmu


def parse_xml(xml_text):
    # Parse the xml text and time stamp
    root = ET.fromstring(xml_text)
    danmu = []
    # Write the danmu to a file
    filepath=os.path.join(bvid,"danmu.txt")
    with open(filepath, 'w', encoding='utf-8') as file:
        for d in root.findall('d'):
            file.write(d.text + '\n')
            danmu.append(d.text)
    return danmu

def get_data(bvid):
    return get_video_data(bvid),get_video_comment(bvid),get_video_dm(get_cid(bvid))

if __name__ == '__main__':
    bvid='BV1dD421J7F1'
    # Create a folder to store the data
    if not os.path.exists("Data"):
        os.makedirs("Data")
    os.chdir("Data")
    if not os.path.exists(bvid):
        os.makedirs(bvid)
    HEADERS=update_headers_with_cookies(HEADERS) # 获取cookies
    video_info,video_comment,video_danmu=get_data(bvid)
