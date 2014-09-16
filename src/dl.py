#!/usr/bin/env python3

import feedparser
import json
from time import mktime
from datetime import datetime
from itertools import takewhile
import string
import os
from subprocess import call

DL_FOLDER_NAME = "~/Downloads/"

VALID_CHARS = "-_.() {}{}".format(string.ascii_letters, string.digits)


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
    clean_chars = (c for c in filename if c in VALID_CHARS)
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
    #last_check_time = datetime(year=2014, month=5, day=14, hour=20, minute=00)
    predicate = is_post_later_than_moment(last_check_time)
    posts = []
    for podcast, params in feeds.items():
        feed = feedparser.parse(params['url'])
        if "skip_promo" in params and params["skip_promo"]:
            entries = feed.entries[1:]
        else:
            entries = feed.entries
        new_posts = list(takewhile(predicate, entries))
        print("\n{} podcast has {} posts later than {}".format(podcast, len(new_posts), last_check_time))
        for post in new_posts:
            link = get_file_link(post)
            pub_time = post.published if "published" in post else post.updated
            print("\n\ttitle: '{}'\n\tpublished: {}\n\tlink: {}".format(
                post.title,
                pub_time,
                link
            ))
            posts.append((post.title, pub_time, link))
    return posts


def posts_to_wget_commands(posts):
    for title, _, download_link in posts:
        if download_link.endswith(".mp3"):
            filename = download_link.split("/")[-1]
        else:
            filename = clean_filename(title) + ".mp3"
        yield "wget '{0}' -O '{1}'".format(download_link, filename)


def download_podcasts(posts):
    if not os.path.isdir(DL_FOLDER_NAME):
        os.mkdir(DL_FOLDER_NAME)
    os.chdir(DL_FOLDER_NAME)
    get_podcast_shell_script_filename = "get_podcasts.sh"
    with open(get_podcast_shell_script_filename, "w+") as fd:
        fd.write('\n'.join(posts_to_wget_commands(posts)))
    return_code = call(["bash", get_podcast_shell_script_filename])
    os.remove(get_podcast_shell_script_filename)
    return return_code


def main():
    state_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "state.json"
    )
    with open(state_path, "r") as fh:
        state = json.loads(fh.read())
    all_posts = check_for_new_posts(state)
    start_time = int(datetime.now().timestamp())
    if confirm(prompt_str="Download new podcasts?", allow_empty=True, default=False):
        return_code = download_podcasts(all_posts)
        print(
            "wget finished downloading with exit code {0}"
            .format(return_code)
        )
        if int(return_code) == 0:
            print("Updating state.json")
            with open(state_path, "w") as fh:
                state["last_download"] = start_time
                fh.write(json.dumps(state, indent=2))
            print("Download completed!")

if __name__ == '__main__':
    main()
