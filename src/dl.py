#!/usr/bin/env python3

import feedparser
import json
from time import mktime
from datetime import datetime
from itertools import takewhile
import string
import os
from subprocess import call

valid_chars = "-_.() {}{}".format(string.ascii_letters, string.digits)


def confirm(prompt_str="Confirm", allow_empty=False, default=False):
    fmt = (prompt_str, 'y', 'n') if default else (prompt_str, 'n', 'y')
    if allow_empty:
        prompt = '%s [%s]|%s: ' % fmt
    else:
        prompt = '%s %s|%s: ' % fmt

    while True:
        ans = input(prompt).lower()

        if ans == '' and allow_empty:
            return default
        elif ans == 'y':
            return True
        elif ans == 'n':
            return False
        else:
            print('Please enter y or n.')


def clean_filename(filename):
    clean_chars = (c for c in filename if c in valid_chars)
    ws_to_us = ("_" if c == " " else c for c in clean_chars)
    return "".join(ws_to_us)


def struct_time_to_datetime(struct):
    return datetime.fromtimestamp(mktime(struct))


def timestamp_to_datetime(ts):
    return datetime.fromtimestamp(ts)


def is_post_later_than_moment(after):
    def func(post):
        moment = post.get("published_parsed", post.get("updated_parsed", None))
        if moment is not None:
            return struct_time_to_datetime(moment) > after
        else:
            raise ValueError
    return func


def get_file_link(post):
    return next(l.href for l in post.links if l.type == 'audio/mpeg')


def check_for_new_posts(_state):
    feeds = _state["feeds"]
    last_check_time = datetime.fromtimestamp(_state["last_download"])
    # last_check_time = datetime(year=2014, month=2, day=23)
    predicate = is_post_later_than_moment(last_check_time)
    posts = []
    for podcast, params in feeds.items():
        feed = feedparser.parse(params['url'])
        new_posts = list(takewhile(predicate, feed.entries))
        print("{} podcast has {} posts later than {}".format(podcast, len(new_posts), last_check_time))
        for post in new_posts:
            link = get_file_link(post)
            pub_time = post.published if "published" in post else post.updated
            print("\tpost with title '{}' published at {}, link: {}".format(
                post.title,
                pub_time,
                link
            ))
            posts.append((post.title, pub_time, link))
    return posts

if __name__ == '__main__':
    with open("state.json", "r") as fh:
        state = json.loads(fh.read())
    all_posts = check_for_new_posts(state)
    start_time = int(datetime.now().timestamp())
    if confirm(prompt_str="Download new podcasts?", allow_empty=True, default=False):
        dl_folder_name = "podcasts"
        if not os.path.isdir(dl_folder_name):
            os.mkdir(dl_folder_name)
        os.chdir(dl_folder_name)
        full_links = [post[2] for post in all_posts]
        print("Starting downloading %d podcasts" % len(full_links))
        with open("links.tmp", "w+") as fd:
            fd.write('\n'.join(full_links))
        return_code = call(["wget", "-i", "links.tmp"])
        os.remove("links.tmp")
        print(
            "wget finished downloading {0} pictures with exit code {1}"
            .format(len(full_links), return_code)
        )
        for title, date, download_link in all_posts:
            if ".mp3?" in download_link:
                os.rename(
                    download_link.split("/")[-1],
                    clean_filename(title) + ".mp3")
        print("Updating state.json")
        with open("../state.json", "w") as fh:
            state["last_download"] = start_time 
            fh.write(json.dumps(state, indent=2))
        print("Download completed!")
