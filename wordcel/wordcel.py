#!/usr/bin/env python3
import sys
import yaml
import re
import os
import os.path
from bs4 import BeautifulSoup as bs
from colorama import init, Fore
from jinja2 import Template

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

# Initialize colorama.
init(autoreset=True)


def usage():
    print(Fore.GREEN + "./wordcel.py test.wc > test.html")


def warn(msg):
    print(Fore.YELLOW + "Warning: " + msg)


def error(msg):
    print(Fore.RED + "Error: " + msg)


def readFile(path):
    with open(path, 'r') as f:
        contents = f.read()
    return contents


def writeFile(path, contents):
    with open(path, 'w') as f:
        f.write(contents)


def prettify(html):
    soup = bs(str(html), features='lxml')
    return soup.prettify()


def splitHeader(doc):
    try:
        header, body = doc.split('---', 1)
    except ValueError:
        warn('YAML Header is missing.')
        return None, doc.strip()
    return header.strip(), body.strip()


def parseHeader(header):
    required_keys = ['title', 'subtitle',
                     'abstract', 'author', 'date', 'template']

    hDict = yaml.safe_load(header)
    for k in required_keys:
        if k not in hDict.keys():
            error('Missing required key \"{}\" in header metadata.'.format(k))
            return None
    return hDict


def splitBlocks(s):
    return re.split('[\n]{2,}', s)


def splitParse(s, start, stop, on, off):
    html = ''
    # NOTE(Jordan): This has a bug. If you only have the start delimiter,
    # it will still apply on() to the rest of the line.
    # Try this: '## Hello, Jor*dan'
    # You'll get italics that you shouldn't get.
    for i, match in enumerate(re.split(f'{start}|{stop}', s)):
        if i % 2 == 1:
            html += on(match)
        else:
            html += off(match)
    return html


def parseNormal(s):
    return s.strip()


def parseLatex(s):
    from io import BytesIO
    import matplotlib.pyplot as plt

    # matplotlib: force computer modern font set
    plt.rc('mathtext', fontset='cm')

    def tex2svg(formula, fontsize=40, dpi=300):
        """Render TeX formula to SVG.
        Args:
            formula (str): TeX formula.
            fontsize (int, optional): Font size.
            dpi (int, optional): DPI.
        Returns:
            str: SVG render.
        """

        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, r'${}$'.format(formula), fontsize=fontsize)

        output = BytesIO()
        fig.savefig(output, dpi=dpi, transparent=True, format='svg',
                    bbox_inches='tight', pad_inches=0.0)
        plt.close(fig)

        output.seek(0)
        return output.read()

    # Change height to 2em. Change width to auto.
    svgStr = tex2svg(s).decode('utf-8')

    # Replace height="123.4323" with height="1.5em".
    svgStr = re.sub('height[\s]*=\"[^"]+\"', 'height="1.5em"', svgStr)
    # Replace width="123.4323" with width="auto".
    svgStr = re.sub('width[\s]*=\"[^"]+\"', 'width="auto"', svgStr)
    return '<span id="inline-svg">'+svgStr+'</span>'


def parseImage(s):

    re_caption = '\!\[.*\]'
    caption = re.search(re_caption, s).group()
    caption = caption.strip('![]')

    re_meta = '\(.*\)'
    meta = re.search(re_meta, s).group()
    meta = meta.strip('()')

    filename, width = meta.split(':')
    html = '<img src={} alt="{}" style="width:{}; height:auto;">'.format(
        filename.strip(), caption.strip(), width.strip())
    if caption.strip() != '':
        html += '\n<span class="caption"><i>{}</i></span>'.format(
            caption.strip())

    return html


def parseVideo(s):
    re_caption = '\?\[.*\]'
    caption = re.search(re_caption, s).group()
    caption = caption.strip('?[]')

    re_meta = '\(.*\)'
    meta = re.search(re_meta, s).group()
    meta = meta.strip('()')

    filename, width = meta.split(':')
    html = '<video autoplay muted loop title="{}" style="width: {}; height: auto;"><source src="{}" type="video/mp4">'.format(
        caption.strip(), width.strip(), filename.strip())
    if caption.strip() != '':
        html += '\n<span class="caption"><i>{}</i></span>'.format(
            caption.strip())

    return html


def parseLink(s):
    re_caption = '\[.*\]'
    caption = re.search(re_caption, s).group()
    caption = caption.strip('[]')

    re_meta = '\(.*\)'
    meta = re.search(re_meta, s).group()
    contents = meta.strip('()')

    html = '<a href="{}">{}</a>'.format(
        contents.strip(), caption.strip())
    return html


def parseItalic(s):
    reItalic = r'(^|[^\*])\*[^\*]+\*[^\*]'
    while re.search(reItalic, s):
        contents = re.search(reItalic, s).group().strip('*')
        html = '<i>'+contents+'</i>'
        s = re.sub(reItalic, html, s, 1)
    return s


def parseStrong(s):
    reStrong = r'(^|[^\*]?)\*\*[^\*]+\*\*[^\*]'
    while re.search(reStrong, s):
        contents = re.search(reStrong, s).group().strip('*')
        html = '<strong>'+contents+'</strong>'
    return s


def parseInlineMath(s):
    reMath = r'(^|[^\*]?)\$\$[^\*]+\$\$[^\*]'
    while re.search(reMath, s):
        contents = re.search(reMath, s).group().strip(' $')
        html = parseLatex(contents)
        s = re.sub(reMath, html, s, 1)
    return s


def parseImages(s):
    reImage = r'\!\[[^\]]*\]\([^\)]*\)'
    while re.search(reImage, s):
        contents = re.search(reImage, s).group().strip()
        html = parseImage(contents)
        s = re.sub(reImage, html, s, 1)
    return s


def parseVideos(s):
    reVideo = r'\?\[[^\]]*\]\([^\)]*\)'
    while re.search(reVideo, s):
        contents = re.search(reVideo, s).group().strip()
        html = parseVideo(contents)
        s = re.sub(reVideo, html, s, 1)
    return s


def parseLinks(s):
    reLink = r'\[[^\]]*\]\([^\)]*\)'
    while re.search(reLink, s):
        contents = re.search(reLink, s).group().strip()
        html = parseLink(contents)
        s = re.sub(reLink, html, s, 1)
    return s


def parseText(s):
    #s = parseItalic(s)
    #s = parseStrong(s)
    s = parseInlineMath(s)
    s = parseImages(s)
    s = parseVideos(s)
    s = parseLinks(s)

    s = re.sub('---', '&mdash;', s)
    return s


def parseTextBlock(block):
    html = ''
    for line in block.strip().split('\n'):
        isHeading = False
        for h in range(6, 0, -1):
            regex = '^#{'+str(h)+'}\s.+'
            matches = re.findall(regex, line, re.MULTILINE)
            for match in matches:
                hContent = parseText(match[h+1:])
                html += '<h{}>{}</h{}>\n'.format(h, hContent, h)
                isHeading = True
        if not isHeading:
            html += '<p>'+parseText(line)+'</p>'
    html = html.strip()
    return '<section>'+html+'</section>'


def parseCodeBlock(block):
    # Get the language name from the first line.
    lexerName, block = block.split('\n', 1)
    # Lookup the correct lexer.
    lexer = get_lexer_by_name(lexerName, stripall=True)
    # Highlight the code.
    block = highlight(block, lexer, HtmlFormatter())
    return '<section><code>'+block+'</code></section>'


def parseAsideBlock(block):
    return '<aside>'+parseTextBlock(block)+'</aside>'


def parseBlockquote(block):
    return '<blockquote>'+parseTextBlock(block)+'</blockquote>'


def parseBlock(block):
    block = block.strip()

    # Code Block
    if block[:3] == '```' and block[-3:] == '```':
        return parseCodeBlock(block.strip('`'))
    # Aside Block
    elif block[:3] == '~~~' and block[-3:] == '~~~':
        return parseAsideBlock(block[3:-3].strip())
    # Block Quote
    elif block[:3] == '"""' and block[-3:] == '"""':
        return parseBlockquote(block[3:-3].strip())
    # Text Block
    else:
        return parseTextBlock(block)


def parseBody(body):
    blocks = splitBlocks(body)
    html = ''.join([parseBlock(b) for b in blocks])
    return html


def parseDocument(doc):
    doc = doc.replace('\r', '')

    header, body = splitHeader(doc)

    headerDict = parseHeader(header)
    if headerDict is None:
        return None

    bodyHTML = parseBody(body)

    return headerDict, bodyHTML


def replaceExtension(path, newExtension):
    return os.path.splitext(path)[0] + newExtension


def wc2html(inFile, outFile, templatesDir):
    wcContents = readFile(inFile)

    hDict, bodyHTML = parseDocument(wcContents)

    templatePath = os.path.join(templatesDir, hDict['template'])

    template = Template(readFile(templatePath))
    docHTML = template.render(title=hDict['title'],
                              subtitle=hDict['subtitle'],
                              body=bodyHTML)
    #docHTML = prettify(docHTML)

    writeFile(outFile, docHTML)
    return hDict


if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        exit()

    wcFilename = sys.argv[1]
    htmlFilename = sys.argv[2]

    wc2html(wcFilename, htmlFilename)
