#!/usr/bin/env python3
import sys
import html
import yaml
import re
import os
import os.path
from bs4 import BeautifulSoup as bs
from colorama import init, Fore
from jinja2 import Template

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, get_all_lexers
from pygments.formatters import HtmlFormatter

# Initialize colorama.
init(autoreset=True)

global hManager

#################
# Parsing Tools #
#################

class HeadingManager():
    def __init__(self):
        self._reset_state()

    def _reset_state(self):
        self.state = [0]*6

    def _get_current_level(self):
        N = len(self.state)
        for i in range(0, N):
            if self.state[i] == 0:
                return max(0, i-1)
        return N-1

    def _update_state(self, h):
        l = self._get_current_level()
        N = len(self.state)

        if h < l:
            for i in range(h+1, N):
                self.state[i] = 0 
        self.state[h] += 1

    def _get_state_as_string(self):
        l = self._get_current_level()
        if l == 0:
            return str(self.state[l]) + '.'
        return '.'.join([str(x) for x in self.state[0:l+1]])

    def getHeadingString(self, h):
        self._update_state(h)
        l = self._get_current_level()
        return self._get_state_as_string()


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

##########################
# Document-level parsing #
##########################

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


def splitParse(s, delim, yes, no):
    return ''.join([
        yes(ss) if i % 2 == 1 else no(ss)
        for (i, ss) in enumerate(re.split('(?<!\\\\)' + delim, s))
    ])


def parseBody(s):
    return parseHTMLOrBlock(s)


def parseDocument(doc):
    doc = doc.replace('\r', '')

    header, body = splitHeader(doc)

    headerDict = parseHeader(header)
    if headerDict is None:
        return None

    global hManager
    hManager = HeadingManager()

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


#######################
# Block-level parsing #
#######################

def parseHTMLOrBlock(s):
    return splitParse(s, '\n\\?\\?\\?\n', parseHtmlBlock, parseCodeOrBlock)


def parseHtmlBlock(s):
    return s


def parseCodeOrBlock(s):
    return splitParse(s, "\n```", parseCodeBlock, parseMathOrBlock)


def parseCodeBlock(s):
    # Get the language name from the first line.
    lexerName, s = s.split('\n', 1)
    # Lookup the correct lexer.
    lexer = get_lexer_by_name(lexerName, stripall=True)
    # Highlight the code.
    s = highlight(s, lexer, HtmlFormatter())
    return '<section class="code">'+s+'</section>'

def parseMathOrBlock(s):
    return splitParse(s, r"\n\$\$\$", parseMathBlock, parseBlockquoteOrBlock)


def parseMathBlock(s):
    s = s.strip('$ \n')
    return '$$' + s + '$$'


def parseBlockquoteOrBlock(s):
    return splitParse(s, r"\n\"\"\"", parseBlockquoteBlock, parseAsideOrBlock)


def parseBlockquoteBlock(s):
    return '<blockquote>%s</blockquote>' % parseLinkOrSpan('"'+s.strip('" ')+'"')


def parseAsideOrBlock(s):
    return splitParse(s, r"\n~~~", parseAsideBlock, parseTextBlocks)


def parseAsideBlock(s):
    return '<aside>%s</aside>' % parseParagraph(s.strip('~ '))


def parseTextBlocks(s):
    return ''.join((parseTextBlock(ss.strip()) for ss in s.split('\n\n')))


def parseTextBlock(s):
    global hManager

    if len(s.split()) == 0:
        return ''
    for h in range(6, 0, -1):
        if s[:h] == '#'*h:
            text = parseLinkOrSpan(s[h:])
            hstr = hManager.getHeadingString(h-1)
            return f'<h{h}><span id=h{h}-label>{hstr}</span>&nbsp;{text}</h{h}>'

    return parseParagraph(s)


#######################
# Span-level parsing #
#######################

def parseParagraph(s):
    return '<p>'+parseCodeOrSpan(s)+'</p>'


def parseCodeOrSpan(s):
    return splitParse(s, r'`', parseCode, parseMathOrSpan)


def parseCode(s):
    s = s.strip('` ')
    # Guess the lexer.
    lexer = get_lexer_by_name('cpp', stripall=True)
    # Highlight the code.
    s = highlight(s, lexer, HtmlFormatter(nowrap=True))
    return '<span class="highlight" style="display: inline-block; padding-left: .3em; padding-right: .3em;">'+s+'</span>'


def parseMathOrSpan(s):
    return splitParse(s, r'\$', parseMath, parseImageOrSpan)


def parseMath(s, height="1.5em"):
    return '$'+s+'$'


def parseImageOrSpan(s):
    return splitParse(s, r'(\!\[.*\]\(.*\))', parseImage, parseLinkOrSpan)


def parseImage(s):
    match = re.search(r'\!\[(.*)\]\((.*)\)', s)
    alt = match.group(1)
    meta = match.group(2)

    if ':' in meta:
        filename, width = meta.split(':')
    else:
        filename = meta
        width = 'auto'

    extension = os.path.splitext(filename)[1].lower()
    if extension in ['.jpg', '.png', '.svg', '.bmp', '.gif', '.tif']:
        html = '<img class="post-img" src={} alt="{}" style="width:{}; height:auto;">'.format(
            filename.strip(), alt.strip(), width.strip())
        if alt.strip() != '':
            html += '\n<span class="caption" style="width:{};">{}</span>'.format(
                width.strip(), alt.strip())
    elif extension in ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.webm']:
        html = '<video autoplay playsinline muted loop title="{}" style="width: {}; height: auto;"><source src="{}" type="video/{}" /></video>'.format(
            alt.strip(), width.strip(), filename.strip(), extension.strip('.'))
        if alt.strip() != '':
            html += '\n<span class="caption" style="width:{};">{}</span>'.format(
                width.strip(), alt.strip())
    return html


def parseLinkOrSpan(s):
    return splitParse(s, r'(\[.*\]\(.*\))', parseLink, parseEmOrSpan)


def parseLink(s):
    match = re.search(r'\[(.*)\]\((.*)\)', s)
    if match:
        alt = match.group(1)
        href = match.group(2)
        return f'<a href="{href}" alt="{alt}">{alt}</a>'
    else:
        warn('Failed to parse link: {}' % s)
        return s


def parseEmOrSpan(s):
    return splitParse(s, r'_', parseEm, parseStrongOrSpan)


def parseEm(s):
    return f'<em>{s}</em>'


def parseStrongOrSpan(s):
    return splitParse(s, r'\*', parseStrong, parseSarcasmOrSpan)


def parseStrong(s):
    return f'<strong>{s}</strong>'


def parseSarcasmOrSpan(s):
    return splitParse(s, r'\\s', parseSarcasm, parseSpan)

def parseSarcasm(s):
    s = re.sub(r'\\s', r'', s)
    return parseStrong(''.join(c.upper() if i%2==0 else c.lower() for i, c in enumerate(s)))

def parseSpan(s):
    s = re.sub(r'---', r'&mdash;', s)
    return s


if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        exit()

    wcFilename = sys.argv[1]
    htmlFilename = sys.argv[2]

    wc2html(wcFilename, htmlFilename)
