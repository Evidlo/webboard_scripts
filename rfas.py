#!/bin/env python3

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from webboard import login, base_url, webboard_url
import creds
from urllib.parse import urljoin
from lxml.html.soupparser import fromstring
import requests
from pony.orm import (
    Database, Required, Set, db_session, Optional, desc, count
)
from datetime import datetime

s = login(creds.username, creds.password)
result = s.get(urljoin(base_url, webboard_url))

years = ['2017', '2018', '2019']
past_semesters = sum([['1' + year + '1', '1' + year + '8'] for year in years], [])
past_semesters_str = sum([[year + 's', year + 'f'] for year in years], [])
# semester start dates
dates_start = [
    # '2016-01-18',
    # '2016-08-22',
    '2017-01-17',
    '2017-08-28',
    '2018-01-16',
    '2018-08-27',
    '2019-01-16',
]
dates_start = [datetime.strptime(date, '%Y-%m-%d') for date in dates_start]

database='cache_rfas.sqlite'
db = Database()
# db.bind(provider='sqlite', filename=database, create_db=True)
db.bind(provider='sqlite', filename=':memory')

class User(db.Entity):
    def __repr__(self):
        return 'User: ' + self.name + (' ({})'.format(self.user_type) if self.user_type else '')

    name = Required(str)
    user_type = Optional(str)
    posts = Set('Post')
    topics = Set('Topic')

class Topic(db.Entity):
    def __repr__(self):
        return 'Topic: ' + self.title

    author = Required(User)
    date_created = Required(datetime)
    date_last_reply = Optional(datetime, nullable=True)
    posts = Set('Post')
    topic_type = Optional(str, nullable=True)
    title = Required(str)
    url = Required(str)
    topic_id = Required(str)

class Post(db.Entity):
    def __repr__(self):
        return 'Post: ' + self.content[:20] + ('...' if len(self.content) > 20 else '')

    author = Required(User)
    topic = Required(Topic)
    date = Required(datetime)
    content = Required(str)
    read = Required(bool)
    post_id = Required(str)

try:
    db.generate_mapping(create_tables=True)
except Exception as e:
    raise Exception("There is a problem with your database.  Try deleting it") from e

@db_session
def update():
    """Update the database"""

    s = login(creds.username, creds.password)

    for semester in past_semesters:
        print('updating semester:', semester)
        set_term(s, semester)
        result = s.get(urljoin(base_url, webboard_url))
        tree = fromstring(result.content)
        for topic_element in tree.xpath('.//table/tbody/tr'):
            year = int(semester[1:-1])
            add_update_topic(s, topic_element, year)

def set_term(s, term):
    """Tell webboard to display data from another semester"""
    payload = {
        'term_id': term,
        'action': 'set_term'
    }

    s.post(urljoin(base_url, webboard_url), data=payload)


@db_session
def add_update_topic(s, topic_element, year):
    """Update a specific topic from an lxml element"""

    author = topic_element.find('td[2]/nobr').text.lstrip('by ')
    topic_id = topic_element.find('td[2]/a').attrib['href'].lstrip('view-topic.asp?id=')
    date_last_reply_str = topic_element.find('td[6]').text
    date_last_reply = None
    title = topic_element.find('td[2]/a').text
    if date_last_reply_str is not None:
        date_last_reply = datetime.strptime(date_last_reply_str + 'm', '%m/%d %H:%M%p')

    topic = Topic.get(topic_id=topic_id)
    if topic is None:

        if not User.get(name=author):
            User(name=author)

        date_created = datetime.strptime(topic_element.find('td[5]').text + 'm', '%m/%d %H:%M%p')
        topic = Topic(
            author=User.get(name=author),
            topic_id=topic_id,
            url=topic_element.find('td[2]/a').attrib['href'],
            title = topic_element.find('td[2]/a').text,
            topic_type=topic_element.find('td[3]').text,
            date_last_reply=date_last_reply,
            date_created=date_created
        )

        topic.date_created = topic.date_created.replace(year=year)

    elif date_last_reply != topic.date_last_reply:
        topic.date_last_reply = date_last_reply

db_session()._enter()
# comment this to use cache_rfas.sqlite
update()

dates_es = []
dates_es_student = []
for year in years:
    dates_spring = []
    dates_fall = []
    dates_spring_student = []
    dates_fall_student = []
    for t in Topic.select(lambda t: t.date_created.year == year and 'idea' in t.topic_type.lower()).order_by(Topic.date_created):
        if t.date_created.month < 6:
            dates_spring_student.append(t.date_created)
        else:
            dates_fall_student.append(t.date_created)
    for t in Topic.select(lambda t: t.date_created.year == year and 'project approved' in t.topic_type.lower()).order_by(Topic.date_created):
        if t.date_created.month < 6:
            dates_spring.append(t.date_created)
        else:
            dates_fall.append(t.date_created)

    dates_es.append(dates_spring)
    dates_es.append(dates_fall)
    dates_es_student.append(dates_spring_student)
    dates_es_student.append(dates_fall_student)

deltas_es = []
for date_start, dates, dates_student in zip(dates_start, dates_es, dates_es_student):
    deltas = []
    for date in dates:
        delta = (date - date_start)
        # delta = (date - dates_student[0])
        if delta.days < 40 and delta.days >= 0:
            deltas.append(delta.days + delta.seconds / 86400)

    deltas_es.append(deltas)

for deltas in deltas_es:
    plt.plot(deltas, np.cumsum(np.ones(len(deltas))))


plt.legend(past_semesters_str)
plt.title('Total project approvals by day')
plt.xlabel('days since semester start')
plt.grid(True)
plt.show()
