#!/usr/bin/env python3
from wordcel.wordcel import *
import os
import os.path as osp
import shutil
import jinja2

ROOT_DIR = osp.dirname(osp.realpath(__file__))
FONTS_DIR = osp.join(ROOT_DIR,     'fonts')
POSTS_DIR = osp.join(ROOT_DIR,     'posts')
IMAGES_DIR = osp.join(ROOT_DIR,    'images')
FILES_DIR = osp.join(ROOT_DIR,     'files')
CSS_DIR = osp.join(ROOT_DIR,       'css')
TEMPLATES_DIR = osp.join(ROOT_DIR, 'templates')
BUILD_DIR = osp.join(ROOT_DIR,     'build')


def glob(directory, extensions):
    return [osp.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if osp.splitext(f)[1].lower() in extensions]

def globEverything(directory):
    return [osp.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames]

def copyTree(src, dst):
    return shutil.copytree(src, dst, dirs_exist_ok=True)

def getPosts():
    return glob(POSTS_DIR, ['.wc'])

def createBuildDir():
    if osp.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.mkdir(BUILD_DIR)
    return BUILD_DIR

def copyFiles(files, dst):
    for f in files:
        shutil.copy(f, dst)

def main():
    postFiles  = getPosts()

    createBuildDir()

    copyTree(POSTS_DIR, BUILD_DIR)
    copyTree(IMAGES_DIR, BUILD_DIR)
    copyTree(CSS_DIR, BUILD_DIR)
    copyTree(FONTS_DIR, BUILD_DIR)
    copyTree(FILES_DIR, BUILD_DIR)

    posts = []
    for src in postFiles:
        name = replaceExtension(osp.basename(src), '.html')
        dst = osp.join(BUILD_DIR, name)

        try:
            postDict = wc2html(src, dst, TEMPLATES_DIR)
        except Exception as e:
            warn(f'Failed to compile file: {src}\n{e}')

            continue
        post_info = [postDict['title'], postDict['date'], name, postDict['abstract']]
        posts.append(post_info)
    posts.sort(key=lambda p: p[1], reverse=True)

    # Render index.html and copy it to the build directory.
    indexTemplate = jinja2.Template( readFile(osp.join(TEMPLATES_DIR, 'index.html')) )
    indexHTML = indexTemplate.render(posts=posts)
    writeFile(osp.join(BUILD_DIR, 'index.html'), indexHTML)

if __name__=='__main__':
    main()
