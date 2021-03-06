#!/bin/env python3
# Evan Widloski - 2018-09-01
# Script for parsing Web Board

from pony.orm import (
    Database, Required, Set, db_session, Optional, desc, count
)
import creds
import regex
import argparse
from IPython import embed
from datetime import datetime
from unidecode import unidecode

import requests
from urllib.parse import urljoin
from lxml.html.soupparser import fromstring
import os
import shutil
import textwrap

base_url = 'https://courses.engr.illinois.edu/ece445/pace/'
webboard_url = 'web-board.asp'
login_url = 'https://courses.engr.illinois.edu/ece445/login.asp'
logout_url = 'https://courses.engr.illinois.edu/ece445/logoutjasp'
database='cache.sqlite'

db = Database()
db.bind(provider='sqlite', filename=database, create_db=True)

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
    content = Optional(str, nullable=True)
    read = Required(bool)
    post_id = Required(str)

try:
    db.generate_mapping(create_tables=True)
except Exception as e:
    raise Exception("There is a problem with your database.  Try the `clean` command") from e


def login(username, password):
    """Login and return a session object"""
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
    """Update a specific topic from an lxml element"""
    author = topic_element.find('td[2]/nobr').text.lstrip('by ')
    topic_id = topic_element.find('td[2]/a').attrib['href'].lstrip('view-topic.asp?id=')

    date_last_reply_str = topic_element.find('td[6]').text
    date_last_reply = None
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

    elif date_last_reply != topic.date_last_reply:
        topic.date_last_reply = date_last_reply
    else:
        return

    print('downloading topic {} - {}'.format(topic.topic_id, topic.title))

    result = s.get(urljoin(base_url, topic.url))
    try:
        tree = fromstring(unidecode(result.content.decode('utf8')))
    except:
        print('failed to parse topic - {}'.format(topic.topic_id))
        return
    with open('/tmp/dump', 'wb') as f:
        f.write(result.content)

    for post_element in tree.xpath('.//div[@id="post_container"]/div[@class="item"]'):
        # post_id = regex.match(
        #     '.*post: \'([0-9]+)\'.*',
        #     post_element.find('div/a').attrib['onclick']
        # ).groups()[0]

        # post_id got deleted with latest update, use author name and date as id instead
        date = post_element.find('div[@class="header"]/div[@class="date"]').text
        date = datetime.strptime(date, '%m/%d/%Y %H:%M:%S %p')
        author = post_element.find('div[@class="header"]/div[@class="author"]').text
        post_id = '{}{}'.format(date, author)

        # add new posts to db
        if not post_id in [p.post_id for p in topic.posts]:
            try:
                user_type = regex.match('.+ \((.*)\)', author).groups()[0]
                author = regex.sub(' \((.*)\)', '', author)
            except Exception as e:
                raise Exception('Could not parse author: {}'.format(author)) from e

            # if user doesn't already exist, create it
            if not User.get(name=author):
                User(name=author, user_type=user_type)
            else:
                User.get(name=author).user_type = user_type

            Post(
                author=User.get(name=author),
                date=date,
                content=''.join(post_element.find('div[@class="post_content"]').itertext()),
                topic=topic,
                read=False,
                post_id=post_id
            )


@db_session
def update(args):
    """Update the database"""

    s = login(creds.username, creds.password)
    result = s.get(urljoin(base_url, webboard_url))
    tree = fromstring(result.content)
    # set all posts as 'read'
    all_posts = Post.select()
    for p in all_posts:
        p.read = True

    for topic_element in tree.xpath('.//table/tbody/tr'):
        add_update_topic(s, topic_element)

@db_session
def replies(args):
    """Check for new posts in topics you have posted in"""

    # topics which you have posted in
    my_topics = Topic.select(lambda t: creds.name in (p.author.name for p in t.posts))
    new_topics = my_topics.filter(lambda t: False in (p.read for p in t.posts))
    if len(new_topics) == 0:
        print("No new posts in your conversations since last update")
    else:
        for t in new_topics:
            new_posts = t.posts.select(lambda p: not p.read).order_by(Post.date)
            print("{} new posts in topic \"{}\"\n".format(len(new_posts), t.title))
            for post in new_posts:
                print(
                    "    " + post.author.name[:18].ljust(20) +
                    ": " +
                    post.content[:40] +
                    ("..." if len(post.content) > 40 else "")
                )
            print("")


def clean(args):
    """Delete the database"""

    os.remove(database)

def shell(args):
    """Enter ipython shell after opening database"""

    db_session()._enter()
    embed()

@db_session
def ta_posts(args):
    """Show number of posts for each TA"""

    tas = User.select(
        lambda u: u.user_type == 'ta'
    ).order_by(lambda u: desc(count(u.posts)))
    for ta in tas:
        print(str(len(ta.posts)).ljust(4), ta.name)


@db_session
def student_posts(args):
    """Show number of posts for each student"""

    students = User.select(
        lambda u: u.user_type == 'student'
    ).order_by(lambda u: desc(count(u.posts)))
    for student in students:
        print(str(len(student.posts)).ljust(4), student.name)

@db_session
def post_search(args):
    posts = Post.select(lambda p: args.string.lower() in p.content.lower())
    for post in posts:
        print(textwrap.indent(textwrap.fill('> ' + post.content), '    '), "\n")

@db_session
def posts(args):
    """Show all posts from a particular user"""

    if User.select(lambda u: u.name == args.name).count() > 0:
        pass

        topics = Topic.select(lambda t: args.name in (p.author.name for p in t.posts))
        for topic in topics:
            posts = topic.posts.select(lambda p: args.name == p.author.name)
            print("{} posts in topic \"{}\"".format(posts.count(), topic.title), "\n")
            for post in posts:
                print(textwrap.indent(textwrap.fill('> ' + post.content), '    '), "\n")
    else:
        print("No posts found by user {}".format(args.name))



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Append -h to any command to view its syntax.")
    parser._positionals.title = "commands"

    subparsers = parser.add_subparsers()
    subparsers.dest = 'command'
    subparsers.required = True

    update_parser = subparsers.add_parser('update', help="update database with new posts/topics")
    update_parser.set_defaults(func=update)

    clean_parser = subparsers.add_parser('clean', help="clear the database")
    clean_parser.set_defaults(func=clean)

    shell_parser = subparsers.add_parser('shell', help="shell for interacting with database")
    shell_parser.set_defaults(func=shell)

    replies_parser = subparsers.add_parser('replies', help="print new replies since last update")
    replies_parser.set_defaults(func=replies)

    ta_posts_parser = subparsers.add_parser('ta_posts', help="print TA post count")
    ta_posts_parser.set_defaults(func=ta_posts)

    student_posts_parser = subparsers.add_parser('student_posts', help="print student post count")
    student_posts_parser.set_defaults(func=student_posts)

    posts_parser = subparsers.add_parser('posts', help="print all posts by user")
    posts_parser.add_argument('name', metavar='name', type=str, help="Full name of user")
    posts_parser.set_defaults(func=posts)

    post_search_parser = subparsers.add_parser('post_search', help="print all posts containing string")
    post_search_parser.add_argument('string', metavar='string', type=str, help="case insensitive string to search for")
    post_search_parser.set_defaults(func=post_search)

    args = parser.parse_args()

    args.func(args)
