#!/usr/bin/env python3

import os

import markdown
import pygments

# Globals
index = []

# Markdown
md = markdown.Markdown(
    encoding='utf=8',
    output_format='html5',
    extensions=[
        'markdown.extensions.codehilite',
        'markdown.extensions.fenced_code',
        'markdown.extensions.meta',
        'markdown.extensions.tables',
        'markdown.extensions.toc',
    ])

# Build
def build_post_markdown(source, target):
    with open(source, 'r') as f:
        text = f.read()
    metadata = {}
    metadata['link'] = target
    content = md.convert(text)
    for k,v in md.Meta.items():
        metadata[k] = v[0]
    index.append(metadata)
    with open('templates/post.html', 'r') as f:
        post = f.read()
        post = post.replace('$date', metadata['date'])
        post = post.replace('$title', metadata['title'])
        post = post.replace('$author', metadata['author'])
        post = post.replace('$content', content)
    with open(target, 'w') as f:
        f.write('<!-- This file has been auto-generated! -->\n')
        f.write(post)

def build_post(path):
    source = os.path.join(path, '_main.md')
    target = os.path.join(path, 'index.html')
    if os.path.isfile(source):
        print('Building: %s' % source)
        build_post_markdown(source, target)

def build_index(target):
    posts = '<thead><td><b>Date</b></td><td><b>Article</b></td></thead>'
    for post in index[::-1]:
        posts += '<tr><td>%s</td><td><a href="%s">%s</a></td></tr>' % (
            post['date'], post['link'], post['title'])
    posts = '<table>%s</table>' % (posts)
    with open('templates/index.html', 'r') as f:
        html = f.read()
        html = html.replace('$posts', posts)
    with open(target, 'w') as f:
        f.write('<!-- This file has been auto-generated! -->\n')
        f.write(html)

def build_all():
    # Create posts
    posts = 'posts'
    for path in os.listdir(posts):
        path = os.path.join(posts, path)
        build_post(path)
    # Create index
    build_index('index.html')

def main():
    build_all()
    return

if __name__ == '__main__':
    main()
