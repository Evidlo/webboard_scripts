from pony.orm import Database, Required, Set, db_session, select, delete, Optional, PrimaryKey
from webboard import *

import requests
from urllib.parse import urljoin
from lxml.html.soupparser import fromstring
from creds import username, password

base_url = 'https://courses.engr.illinois.edu/ece445/pace/'
webboard_url = 'web-board.asp'
login_url = 'https://courses.engr.illinois.edu/ece445/login.asp'

db = Database()
db.bind(provider='sqlite', filename='cache.sqlite3', create_db=True)

class User(db.Entity):
    def __repr__(self):
        return 'User: ' + self.name

    name = Required(str)
    posts = Set('Post')
    topics = Set('Topic')


class Topic(db.Entity):
    def __repr__(self):
        return 'Topic:' + self.title

    author = Required(User)
    date_created = Required(str)
    date_last_reply = Optional(str, nullable=True)
    posts = Set('Post')
    topic_type = Optional(str, nullable=True)
    title = Required(str)
    url = Required(str)
    topic_id = Required(str)

class Post(db.Entity):
    def __repr__(self):
        return 'Post: ' + self.author

    author = Required(User)
    topic = Required(Topic)
    date = Required(str)
    content = Required(str)

db.generate_mapping(create_tables=True)


# login and return a session object
def login(username, password):
    payload = {
        'username': username,
        'password': password,
        'action': 'Login'
    }

    s = requests.Session()
    result = s.post(login_url, data=payload)
    assert b'Your username and password were incorrect' not in result.content, "Incorrect user/pass"
    return s


@db_session
def add_update_topic(s, topic_element):
    author = topic_element.find('td[2]/nobr').text.lstrip('by ')
    topic_id = topic_element.find('td[2]/a').attrib['href'].lstrip('view-topic.asp?id=')
    date_last_reply = topic_element.find('td[6]').text

    topic = Topic.get(topic_id=topic_id)
    if topic is None:

        if not User.get(name=author):
            User(name=author)

        topic = Topic(
            author=User.get(name=author),
            topic_id=topic_id,
            url=topic_element.find('td[2]/a').attrib['href'],
            title = topic_element.find('td[2]/a').text,
            topic_type=topic_element.find('td[3]').text,
            date_created=topic_element.find('td[5]').text,
            date_last_reply=date_last_reply
        )

    elif date_last_reply != topic.date_last_reply:
        topic.date_last_reply = date_last_reply

        topic.posts.clear()
    else:
        return

    print('downloading topic {}'.format(topic.topic_id))

    result = s.get(urljoin(base_url, topic.url))
    tree = fromstring(result.content)

    for post_element in tree.xpath('.//div[@id="post_container"]/div[@class="item"]'):
        author = post_element.find('div[@class="header"]/div[@class="author"]').text
        import ipdb
        ipdb.set_trace()
        author = author.rstrip(' (ta)').rstrip(' (student)').rstrip(' (prof)')

        if not User.get(name=author):
            User(name=author)

        Post(
            author=User.get(name=author),
            date=post_element.find('div[@class="header"]/div[@class="date"]').text,
            content=post_element.find('div[@class="post_content"]/p').text,
            topic=topic
        )


# get dictionary of topics (no posts data)
def update():
    s = login(username, password)
    result = s.get(urljoin(base_url, webboard_url))
    tree = fromstring(result.content)
    for topic_element in tree.xpath('.//table/tbody/tr'):
        add_update_topic(s, topic_element)


if __name__ == '__main__':
    print('checking for updates')
    update()
