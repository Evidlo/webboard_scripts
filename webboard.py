#!/bin/env python3
# Evan Widloski - 2018-08-30
# Parser for ECE445 Web Board
import requests
from urllib.parse import urljoin
from lxml.html.soupparser import fromstring
from creds import username, password
import json
import pickle
import os

base_url = 'https://courses.engr.illinois.edu/ece445/pace/'
webboard_url = 'web-board.asp'
login_url = 'https://courses.engr.illinois.edu/ece445/login.asp'
cache_file = 'cache.json'

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



# get dictionary of topics (no posts data)
def get_current_topics():
    result = s.get(urljoin(base_url, webboard_url))

    tree = fromstring(result.content)

    topics = {}
    for topic_element in tree.xpath('.//table/tbody/tr'):
        topic_id = topic_element.find('td[2]/a').attrib['href'].lstrip('view-topic.asp?id=')

        topics[topic_id] = {
            'url': topic_element.find('td[2]/a').attrib['href'],
            'title': topic_element.find('td[2]/a').text,
            'author': topic_element.find('td[2]/nobr').text.lstrip('by '),
            'type': topic_element.find('td[3]').text,
            'replies': int(topic_element.find('td[4]').text),
            'date_created': topic_element.find('td[5]').text,
            'date_last_reply': topic_element.find('td[6]').text
        }

    return topics


# get dictionary of topics (with posts data) stored on disk
def get_cached_topics():
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)


# compare new and cache topics to decide what topic posts to redownload
def update_topics(current_topics, cached_topics):

    new_changed_topic_ids = []
    unchanged_topic_ids = []
    for topic_id, topic in current_topics.items():
        if (cached_topics is None or
            topic_id not in cached_topics or
            topic['date_last_reply'] != cached_topics[topic_id]['date_last_reply']):
            new_changed_topic_ids.append(topic_id)
        else:
            unchanged_topic_ids.append(topic_id)


    for topic_id in unchanged_topic_ids:
        current_topics[topic_id]['posts'] = cached_topics[topic_id]['posts']

    for n, topic_id in enumerate(new_changed_topic_ids):

        print('downloading topic {}/{}'.format(n + 1, len(new_changed_topic_ids)))
        result = s.get(urljoin(base_url, current_topics[topic_id]['url']))
        tree = fromstring(result.content)

        posts = []
        for post_element in tree.xpath('.//div[@id="post_container"]/div[@class="item"]'):
            post = {
                'author': post_element.find('div[@class="header"]/div[@class="author"]').text,
                'date': post_element.find('div[@class="header"]/div[@class="date"]').text,
                'content': post_element.find('div[@class="post_content"]/p').text
            }

            posts.append(post)

        current_topics[topic_id]['posts'] = posts


def cache_topics(topics):
    with open('cache.json', 'wb') as f:
        pickle.dump(topics, f)


if __name__ == '__main__':
    s = login(username, password)
    current_topics = get_current_topics()
    cached_topics = get_cached_topics()
    update_topics(current_topics, cached_topics)
    cache_topics(current_topics)
