#coding=utf-8

import urllib
from github import Github
import time
import datetime
import requests
import pyrtmp
from fake_useragent import UserAgent
import os
import platform
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

def is_https_link_valid(link):
    result = False 
    error = None 
    try:
        urllib.request.urlopen(url = link, timeout = 3) 
        result = True 
    except urllib.error.URLError as exc: 
        error = 'URL错误: {0}'.format(str(exc)) 
    except urllib.error.HTTPError as exc: 
        error = 'HTTP错误: {0}'.format(str(exc)) 
    except Exception as exc: 
        error = '未知错误: {0}'.format(str(exc))
    if error:
        print(error)
        return False
    return result

def is_http_link_valid(link):
    try:
        fake_headers = {"user-agent": UserAgent().random}
        response = requests.get(link, timeout = (3, 2), headers = fake_headers)
        return response.status_code == 200
    except requests.exceptions.Timeout:
        # 处理超时异常
        print("请求超时")
        return False
    except requests.exceptions.RequestException as e:
        # 处理其他请求异常
        print("请求发生错误:", e)
        return False

def is_rtmp_link_valid(link):
    try:
        rtmp = pyrtmp.RTMP(link)
        rtmp.connect()
        return True
    except:
        return False

def do_search(keywords, iptv_result, end_weeks, begin_weeks = 0):
    new_keywords = keywords.copy()
    for keyword in keywords:
        new_keyword = keyword
        if keyword.isascii():
            if keyword == keyword.upper():
                new_keyword = keyword.lower()
            else:
                new_keyword = keyword.upper()
            new_keywords.append(new_keyword)
        elif is_chinese(keyword):
            new_keyword = simplified_to_traditional(keyword)
            if new_keyword != keyword:
                new_keywords.append(new_keyword)
        print("keywords: " + keyword + new_keyword)
   # 使用 GitHub API 搜索仓库
    repos = g.search_repositories(query = "iptv", sort = "updated", order = "desc")
    today = datetime.date.today()
    early_date = today - datetime.timedelta(weeks = end_weeks)
    late_date = today - datetime.timedelta(weeks = begin_weeks)
    print("from\t" + str(early_date))
    print("to\t" + str(late_date))
    # 打印搜索结果
    for repo in repos:
        print("---" + repo.full_name + "---" + repo.url)
        if (repo.size < 1):
            continue

        start_time = time.perf_counter()
        last_updated = repo.updated_at.date()
        print("update at " + str(last_updated))
        if last_updated  > late_date:
            continue
        
        if (last_updated < early_date):
            break

        # 获取仓库的根目录
        root = repo.get_contents("")
        cost_time = time.perf_counter() - start_time
        print("-get repo %s cost time: %f s" % (repo.full_name, cost_time))
        # 遍历仓库中的所有文件
        while root:
            try:
                content_file = root.pop(0)
                file_name = content_file.name
                if content_file.type == "dir":
                    if file_name != ".github":
                        root.extend(repo.get_contents(content_file.path))
                    continue

                if (file_name.rfind(".m3u") == -1):
                    continue

                need_decode = True
                if (content_file.encoding == "none"):
                    need_decode = False
                elif (content_file.encoding != "base64"):
                    print("\033[1;31m" + file_name + " encoding is " + content_file.encoding + "\033[0m")
                    # other encode here
                    continue
            except Exception as e:
                print("\033[1;31mrepos travel exception:%s!\033[0m"%str(e))
                continue

            start_time = time.perf_counter()
            m3u_content = content_file.decoded_content.decode("utf-8") if need_decode else content_file.content
            line_contents = m3u_content.split("\n")
            cost_time = time.perf_counter() - start_time
            print("get file %s cost time: %f s" % (file_name, cost_time))
            for line_count, item in enumerate(line_contents):
                if not item.startswith("#EXTINF:"):
                    continue

                for keyword in new_keywords:
                    if keyword in item:
                        iptv_result[line_contents[line_count + 1]] = item + "\n"
                        print("\033[1;35m%s\n%s\033[0m"%(item, line_contents[line_count + 1]))
                        break

        if len(iptv_result) > 50:
            print("results up to 50")
            break


all_start_time = time.perf_counter()
# 创建 Github 对象
g = Github("your token here")

iptv_result = dict()
# 定义搜索关键字
keywords = ["凤凰", "台湾", "cnn", "bbc"]
all_keywords = "".join(keywords)
result_count = 0;
if (platform.system() == "Windows"):
    os.system("")
try:
    start_time = time.perf_counter()
    do_search(keywords, iptv_result, 78)
finally:
    cost_time = time.perf_counter() - start_time
    result_count = len(iptv_result)
    print("\033[1;32m-----search keyword %s cost time: %f s with %d results\033[0m" % (all_keywords, cost_time, result_count))
    if not iptv_result:
        print("\033[1;31mresult is empty\033[0m")
        exit(1)

    found_count = 0
    file_name = os.path.dirname(__file__) + "/" + all_keywords + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".m3u"
    file = open(file_name, "w", encoding = 'utf-8')
    file.write('#EXTM3U name="github"\n')
    test_index = 0
    for key, value in iptv_result.items():
        test_index = test_index + 1
        if (value.find("凤凰古城") > 0 or "广播" in value or "凤凰传奇" in value):
        #or value.find("香港") == -1 and value.find("电影") == -1 and value.find("美洲") == -1):
            continue

        print("testing(%d/%d) %s"%(test_index, result_count, value + key))
        if (key.startswith("http") and is_https_link_valid(key) or
            #not isHttps and key.startswith("http") and is_http_link_valid(key) or
            key.startswith("rtmp") and is_rtmp_link_valid(key)):
            file.write(value + key + "\n\n")
            found_count = found_count + 1
            print("\033[1;32mpass\033[0m")
    if (found_count == 0):
        os.remove(file_name)
    else:
        file.close()
    print("-----found %d results cost time: %f s" % (found_count, time.perf_counter() - all_start_time))

