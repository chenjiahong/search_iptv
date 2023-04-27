from github import Github
import time
import datetime
import requests
import pyrtmp
from fake_useragent import UserAgent
import os
import unicodedata
import opencc

def simplified_to_traditional(simplified):
    # 创建一个简体中文到繁体中文的转换器
    converter = opencc.OpenCC('s2t')
    # 转换为繁体中文
    traditional = converter.convert(simplified)
    return traditional

def is_chinese(s):
    """
    判断一个字符串是否全部由中文组成
    """
    for c in s:
        # 如果有一个字符不是中文，则返回False
        if not unicodedata.category(c).startswith('Lo'):
            return False
    return True


def is_http_link_valid(link):
    try:
        fake_headers = {"user-agent": UserAgent().random}
        response = requests.get(link, timeout = (3, 2), headers = fake_headers)
        return response.status_code == 200
    except:
        return False

def is_rtmp_link_valid(link):
    try:
        rtmp = pyrtmp.RTMP(link)
        rtmp.connect()
        return True
    except:
        return False

def do_search(keywords, iptv_result, update_weeks):
    is_sc = is_chinese(keywords[0])
    alt_keywords = keywords.copy()
    if (is_sc):
        index = 0
        for index, keyword in enumerate(keywords):
            alt_keywords[index] = simplified_to_traditional(keyword)
            print(keyword + alt_keywords[index])
   # 使用 GitHub API 搜索仓库
    repos = g.search_repositories(query = "iptv", sort = "updated")
    # 打印搜索结果
    for repo in repos:
        print("---" + repo.full_name + "---" + repo.url)
        if (repo.size < 1):
            continue

        start_time = time.perf_counter()
        n_weeks_ago = datetime.date.today() - datetime.timedelta(weeks = update_weeks)
        if (repo.updated_at.date() < n_weeks_ago):
            break

        contents = repo.get_contents("")
        cost_time = time.perf_counter() - start_time
        print("-get repo %s cost time: %f s" % (repo.full_name, cost_time))
        for content_file in contents:
            file_name = content_file.name
            if (file_name.rfind(".m3u") == -1):
                continue

            if (content_file.encoding != "base64"):
                print(file_name + " is not base64")
                # other encode here
                continue

            start_time = time.perf_counter()
            m3u_content = content_file.decoded_content.decode("utf-8")
            line_contents = m3u_content.split("\n")
            cost_time = time.perf_counter() - start_time
            print("-get file %s cost time: %f s" % (file_name, cost_time))
            for line_count, item in enumerate(line_contents):
                for keyword, alt_keyword in zip(keywords, alt_keywords):
                    if ((keyword in item) or is_sc and (alt_keyword in item)):
                        iptv_result[line_contents[line_count + 1]] = item + "\n"
                        break


all_start_time = time.perf_counter()
# 创建 Github 对象
g = Github("your token here")

iptv_result = dict()
# 定义搜索关键字
keywords = ["凤凰", "台湾"]
try:
    result_count = 0;
    start_time = time.perf_counter()
    do_search(keywords, iptv_result, 54)
    cost_time = time.perf_counter() - start_time
    print("-----search keyword %s cost time: %f s with %d results" % (keywords[0], cost_time, len(iptv_result) - result_count))
    result_count = len(iptv_result)
finally:
    if (not bool(iptv_result)):
        exit(1)

    found_count = 0
    file_name = os.path.dirname(__file__) + "/" + keywords[0] + str(all_start_time) + ".m3u"
    file = open(file_name, "w")
    file.write('#EXTM3U name="github"\n')
    for key, value in iptv_result.items():
        if (value.find("凤凰古城") > 0):
        #or value.find("香港") == -1 and value.find("电影") == -1 and value.find("美洲") == -1):
            continue

        print("--test " + value + key)
        if ("http" in key and is_http_link_valid(key) or "rtmp" in key and is_rtmp_link_valid(key)):
            file.write(value + key + "\n")
            found_count = found_count + 1
    file.close()
    print("-----found %d results cost time: %f s" % (found_count, time.perf_counter() - all_start_time))
