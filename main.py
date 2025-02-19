import requests
import time
from openai import OpenAI
import ast
from dotenv import load_dotenv
import os

# 访问环境变量
url = "https://api.bilibili.com/x/v2/reply/up/fulllist"
del_url = "https://api.bilibili.com/x/v2/reply/del"
load_dotenv()
csrf_token = os.getenv("CSRF_TOKEN")
cookie = os.getenv("COOKIE")
apikey = os.getenv("API_KEY")

# 打印配置，检查是否加载成功
print(csrf_token, cookie)

# 请求头
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9",
    "cookie": cookie,  # 请替换为实际 cookie
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
}


# 发送 GET 请求，获取评论数据
def fetch_comments(oid, page, page_size=10):
    params = {
        "order": 1,
        "filter": -1,
        "type": 1,
        "oid": oid,
        "pn": page,
        "ps": page_size,
        "charge_plus_filter": False
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        return None


# 解析评论数据
def parse_comments(oid):
    page = 1
    response = fetch_comments(oid, page)  # 获取第一页评论
    total = response['data']['page']['total']
    print(f"视频 {oid} 总评论数: {total}")
    data_list = []

    # 使用分页获取所有评论数据
    while len(data_list) < total:
        for item in response['data']['list']:
            data = {
                'rpid': item['rpid'],
                'oid': item['oid'],
                'message': item['content']['message']
            }
            data_list.append(data)
        if len(data_list) < total:
            page += 1  # 下一页
            response = fetch_comments(oid, page)  # 获取下一页评论

    return data_list


# 发送 POST 请求，删除恶意评论
def delete_comment(rpid, oid):
    data = {
        "oid": str(oid),
        "type": "1",  # 假设type是1
        "rpid": str(rpid),
        "jsonp": "jsonp",  # 假设这是固定值
        "csrf": csrf_token  # CSRF Token
    }

    response = requests.post(del_url, headers=headers, data=data)
    if response.status_code == 200:
        print(f"删除成功，rpid: {rpid}")
    else:
        print(f"删除失败，状态码: {response.status_code}")
        print(f"响应内容: {response.text}")


def split_list_by_chunks(lst, chunk_size=10):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


# 调用大模型判断 message 是否善意
def filter_non_positive_comments(data_list):
    client = OpenAI(api_key=apikey,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    # 改为每10条分析一次，不然响应时间太慢了
    completion = client.chat.completions.create(
        model="qwen-long",
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'system', 'content': str(data_list)},
            {'role': 'user',
             'content': '筛选出上面数组中非善意（或潜在不太合适的表达）评论的message数据，按照原数组的格式输出，只要输出数组结果，禁止输出其他文字'}
        ],
        stream=True,
        stream_options={"include_usage": True}
    )

    full_content = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            full_content += chunk.choices[0].delta.content

    print("AI判断结果:", full_content)

    # 使用 ast.literal_eval() 将字符串转换为 Python 列表
    bad_list = ast.literal_eval(full_content)
    return bad_list


# 主程序逻辑
def main():
    oid = "BV1jk4y1Y71A"  # 你的目标视频 ID

    # 分页获取评论数据
    data_list = parse_comments(oid)
    print(f"获取到 {len(data_list)} 条评论数据。")
    # 调用函数进行切片
    sub_lists = split_list_by_chunks(data_list)
    for sub_list in sub_lists:
        # 调用大模型判断恶意评论
        bad_list = filter_non_positive_comments(sub_list)
        print(f"恶意评论数量: {len(bad_list)}")
        print(bad_list)
        # 删除恶意评论
        # for bad_comment in bad_list:
        #     delete_comment(bad_comment['rpid'], bad_comment['oid'])
        #     time.sleep(3)  # 请求间隔 3 秒


if __name__ == "__main__":
    main()
