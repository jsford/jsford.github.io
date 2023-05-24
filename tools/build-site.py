#!/usr/bin/env python3
import os
import os.path as osp
import markdown

def build_post(post_root):
    print(post_root)

def build_site(site_root):
    # Create build directory.

    # Build blog posts.
    posts = os.listdir(osp.join(site_root, 'posts'))
    for post in posts:
        build_post(post)

    # Copy everything into the build directory.

if __name__=='__main__':
    build_site('.')
