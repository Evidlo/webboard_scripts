import requests
from urllib.parse import urljoin
from lxml.html.soupparser import fromstring
from .creds import username, password

base_url = 'https://courses.engr.illinois.edu/ece445/pace/'
webboard_url = 'web-board.asp'

payload = {
    'username': username,
    'password': password,
    'action': 'Login'
}

s = requests.Session()
result = s.post('https://courses.engr.illinois.edu/ece445/login.asp', data=payload)
result = s.get(urljoin(base_url, webboard_url))

tree = fromstring(result.content)

topics = []
for topic_element in tree.xpath('.//table/tbody/tr'):
    topic = {
        'url': topic_element.find('td[2]/a').attrib['href'],
        'title': topic_element.find('td[2]/a').text,
        'author': topic_element.find('td[2]/nobr').text.lstrip('by '),
        'type': topic_element.find('td[3]').text,
        'replies': int(topic_element.find('td[4]').text),
        'date_created': topic_element.find('td[5]').text,
        'date_last_reply': topic_element.find('td[6]').text
    }

    topics.append(topic)

for topic in topics[0:1]:
    result = s.get(urljoin(base_url, topic['url']))
    tree = fromstring(result.content)

    posts = []
    for post_element in tree.xpath('.//div[@id="post_container"]/div[@class="item"]'):
        post = {
            'author': post_element.find('div[@class="header"]/div[@class="author"]').text,
            'date': post_element.find('div[@class="header"]/div[@class="date"]').text,
            'content': post_element.find('div[@class="post_content"]/p').text
        }

        posts.append(post)


# with open('/tmp/dump', 'wb') as f:
#     f.write(result.content)
