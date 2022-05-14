#!/usr/bin/env python3
from wordcel.wordcel import *
import os
import os.path as osp
import shutil
import jinja2

def getProjectRoot():
    return osp.dirname(osp.realpath(__file__))

def glob(directory, extensions):
    return [osp.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if osp.splitext(f)[1].lower() in extensions]

def globEverything(directory):
    return [osp.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames]

def getPosts():
    rootDir = getProjectRoot()
    postsDir = osp.join(rootDir, 'posts')
    return glob(postsDir, ['.wc'])

def getFonts():
    rootDir = getProjectRoot()
    postsDir = osp.join(rootDir, 'fonts')
    return glob(postsDir, ['.ttf','.otf','.woff'])

def getImages():
    imgExtensions = ['.jpg','.png','.gif','.svg','.mp4','.bmp','.tif']
    rootDir = getProjectRoot()

    postsDir = osp.join(rootDir, 'posts')
    images = glob(postsDir, imgExtensions)

    imagesDir = osp.join(rootDir, 'images')
    rootImages = glob(imagesDir, imgExtensions)

    images.extend(rootImages)
    return images

def getMisc():
    miscExtensions = ['.py','.c','.cpp','.h','.hpp']
    rootDir = getProjectRoot()

    postsDir = osp.join(rootDir, 'posts')
    postsFiles = glob(postsDir, miscExtensions)

    filesDir = osp.join(rootDir, 'files')
    files = globEverything(filesDir)

    files.extend(postsFiles)
    return files

def getCSS():
    rootDir = getProjectRoot()
    postsDir = osp.join(rootDir, 'css')
    return glob(postsDir, ['.css'])

def createBuildDir():
    rootDir = getProjectRoot()
    buildDir = osp.join(rootDir, 'build')
    if osp.exists(buildDir):
        shutil.rmtree(buildDir)
    os.mkdir(buildDir)
    return buildDir

def copyFiles(files, dst):
    for f in files:
        shutil.copy(f, dst)

def main():
    postFiles  = getPosts()
    imageFiles = getImages()
    cssFiles   = getCSS()
    fontFiles  = getFonts()
    miscFiles  = getMisc()

    buildDir = createBuildDir()
    posts = []
    for src in postFiles:
        name = replaceExtension(osp.basename(src), '.html')
        dst = osp.join(buildDir, name)

        templatesDir = osp.join(getProjectRoot(), 'templates')
        try:
            postDict = wc2html(src, dst, templatesDir)
        except Exception as e:
            warn(f'Failed to compile file: {src}\n{e}')

            continue
        post_info = [postDict['title'], postDict['date'], name, postDict['abstract']]
        posts.append(post_info)
    posts.sort(key=lambda p: p[1], reverse=True)

    copyFiles(imageFiles, buildDir)
    copyFiles(cssFiles, buildDir)
    copyFiles(fontFiles, buildDir)
    copyFiles(miscFiles, buildDir)

    # Render index.html and copy it to the build directory.
    indexTemplate = jinja2.Template( readFile(osp.join(templatesDir, 'index.html')) )
    indexHTML = indexTemplate.render(posts=posts)
    writeFile(osp.join(buildDir, 'index.html'), indexHTML)

if __name__=='__main__':
    main()
