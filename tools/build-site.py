#!/usr/bin/env python3
import os
<<<<<<< HEAD
import glob
import shutil
import os.path as osp
import markdown
import jinja2


def replace_dir(path):
    if osp.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)


def copytree(src, dst):
    return shutil.copytree(src, dst)


def copyfile(src, dst):
    return shutil.copy2(src, dst)


def read_file(path):
    with open(path, 'r') as file:
        contents = file.read()
    return contents


def write_file(path, string):
    with open(path, 'w') as file:
        file.write(string)
    return


def list_post_dirs(site_root, posts_root='posts'):
    post_dirs = os.listdir(osp.join(site_root, posts_root))
    post_dirs = [osp.abspath(osp.join(site_root, posts_root, pd)) for pd in post_dirs]
    post_dirs.sort()
    return post_dirs


def build_site(site_root, site_dirname):

    site_dir = osp.join(site_root, site_dirname)
    replace_dir(site_dir)

    posts_dirname = 'posts'
    posts_src_dir = osp.join(site_root, posts_dirname)
    posts_dst_dir = osp.join(site_dir, posts_dirname)
    copytree(posts_src_dir, posts_dst_dir)

    assets_dirname = 'assets'
    assets_src_dir = osp.join(site_root, assets_dirname)
    assets_dst_dir = osp.join(site_dir, assets_dirname)
    copytree(assets_src_dir, assets_dst_dir)

    css_dirname = 'css'
    css_src_dir = osp.join(site_root, css_dirname)
    css_dst_dir = osp.join(site_dir, css_dirname)
    copytree(css_src_dir, css_dst_dir)

    copyfile(osp.join(site_root, 'templates/index.html'), site_dir)

    # Construct the blog.html page.
    environment = jinja2.Environment()
    blog_template = environment.from_string( read_file(osp.join(site_root, 'templates/blog.html') ))

    post_dirs = list_post_dirs(site_root, posts_dirname)
    
    blog_page = blog_template.render(posts=[['#','b','c'], ['#','e','f']])
    write_file(osp.join(site_dir, 'blog.html'), blog_page)


if __name__=='__main__':
    build_site('.', 'site')
=======
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
>>>>>>> 7c1a9a36e7ed3ea76e998217b7c92ccd7f2ba589
