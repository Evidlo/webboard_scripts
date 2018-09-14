# Webboard Scraper Tool

### Setup

    pip3 install --user -r requirements.txt
    cp creds.py.example creds.py
    
Update `creds.py` with your credentials

Python 3.5 or greater is required.

### Usage

Update local cache of all posts.  Just run once each time you want to pull new stuff from Web Board.

    $ python3 webboard.py update
    downloading topic 27207
    downloading topic 27340
    downloading topic 27360
    
See number of posts by all students

    $ python3 webboard.py student_posts
    10   John Smith
    10   Michael Foo
    8    Hongyi Bar
    5    Landon Smith
    4    Hosang Smith
 
See all posts by a particular user

    $ python3 webboard.py posts "Evan Widloski"
    1 posts in topic "Problem: Study space availability tracker" 

        > A solution could be something simple like a few PIR sensors pointed
        at different parts of the room.  But this by itself is probably not
        sufficiently complex for a senior design project. 

    2 posts in topic "Cheap remote fireworks launching system" 

        > What goes at the other end of the ethernet cable?  Do users need to
        carry their laptop out into the yard to launch fireworks? 

        > Both the esp8266 and esp32 are capable of acting as both a client
        and AP (access point). 
        
Open database in shell to run custom PonyORM queries

    python3 webboard.py shell
    
    In[1]: list(User.select(lambda u: u.name == 'Evan Widloski').first().posts.order_by(Post.date))[0].date
    Out[1]: datetime.datetime(2018, 8, 27, 9, 13, 34)

    
See list of all commands

    python3 webboard.py -h
