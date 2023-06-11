#!/usr/bin/env python3
import os
import glob
import shutil
import os.path as osp
import markdown
import yaml
import jinja2
from datetime import datetime


def replace_dir(path):
    if osp.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)


def change_extension(path, new_ext):
    base = osp.splitext(path)[0]
    return base + '.' + new_ext


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


class BlogPost:
    def __init__(self, directory, mdfilename, title, description, date, html):
        self.directory = directory
        self.mdfilename = mdfilename
        self.htmlfilename = change_extension(mdfilename, 'html')
        self.title = title
        self.description = description
        self.date = date
        self.html = html


def build_site(site_root, site_dirname):

    # Construct a build directory for the site.
    site_dir = osp.join(site_root, site_dirname)
    replace_dir(site_dir)

    # Copy blog post directories into the build tree.
    posts_dirname = 'posts'
    posts_src_dir = osp.join(site_root, posts_dirname)
    posts_dst_dir = osp.join(site_dir, posts_dirname)
    copytree(posts_src_dir, posts_dst_dir)

    # Copy site assets into the build tree.
    assets_dirname = 'assets'
    assets_src_dir = osp.join(site_root, assets_dirname)
    assets_dst_dir = osp.join(site_dir, assets_dirname)
    copytree(assets_src_dir, assets_dst_dir)

    # Copy css into the build tree.
    css_dirname = 'css'
    css_src_dir = osp.join(site_root, css_dirname)
    css_dst_dir = osp.join(site_dir, css_dirname)
    copytree(css_src_dir, css_dst_dir)

    # Copy the index.html page into the build tree.
    copyfile(osp.join(site_root, 'templates/index.html'), site_dir)

    # Find all of the blog posts.
    post_dirs = list_post_dirs(site_root, posts_dirname)
    posts = []
    for directory in post_dirs:
        mdfiles = glob.glob('*.md', root_dir=directory)
        if len(mdfiles) != 1:
            print("Error: Blog post directory '{directory}' must contain exactly one markdown file.")
        mdfile = mdfiles[0]

        postcontent = read_file(osp.join(directory, mdfile))
        splitcontent = postcontent.split('---', maxsplit=2)
        yamlcontent = splitcontent[1]
        mdcontent = splitcontent[2]
        htmlcontent = markdown.markdown(mdcontent, extensions=['markdown.extensions.tables'])

        # Replace '---' with '&mdash;'
        htmlcontent = htmlcontent.replace('---', '&mdash;')

        header = yaml.load(yamlcontent, Loader=yaml.FullLoader)
        htmldescription = markdown.markdown(header['description']).lstrip('<p>').rstrip('</p>')

        post = BlogPost(directory, mdfile, header['title'], htmldescription, header['date'], htmlcontent)
        posts.append(post)
    posts.sort(key=lambda p : datetime.strptime(p.date, '%B %d, %Y'), reverse=True)

    # Construct the blog.html page and add it to the build tree.
    environment = jinja2.Environment()
    blog_template_string = read_file(osp.join(site_root, 'templates/blog.html'))
    blog_template = environment.from_string( blog_template_string )

    posts_list = []
    for post in posts:
        postpath = osp.join('posts', post.directory.split('/')[-1], post.htmlfilename)
        posts_list.append([postpath, post.title, post.date, post.description])
    
    blog_page = blog_template.render(posts=posts_list)
    write_file(osp.join(site_dir, 'blog.html'), blog_page)

    # Construct a page for each blog post and add it to the build tree.
    for post in posts:
        postpath = osp.join(site_dir, post.htmlfilename)
        post_template_string = read_file(osp.join(site_root, 'templates/post.html'))
        post_template = environment.from_string( post_template_string )

        post_page = post_template.render(title=post.title, date=post.date, contents=post.html)
        postpath = osp.join('posts', post.directory.split('/')[-1], post.htmlfilename)
        write_file(osp.join(site_dir, postpath), post_page)


if __name__=='__main__':
    build_site('.', 'site')
