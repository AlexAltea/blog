#!/usr/bin/env python3

import os

import markdown
import pygments

# Markdown
md = markdown.Markdown(
    encoding='utf=8',
    output_format='html5',
    extensions=[
        'markdown.extensions.codehilite',
        'markdown.extensions.fenced_code',
        'markdown.extensions.meta',
        'markdown.extensions.tables',
    ])

# Build
def build_post_markdown(source, target):
    with open(source, 'r') as f:
        text = f.read()
    metadata = {}
    content = md.convert(text)
    for k,v in md.Meta.items():
        metadata[k] = v[0]
    with open('posts/post.html', 'r') as f:
        post = f.read()
        post = post.replace('$date', metadata['date'])
        post = post.replace('$title', metadata['title'])
        post = post.replace('$author', metadata['author'])
        post = post.replace('$content', content)
    with open(target, 'w') as f:
        f.write('<!-- This file has been auto-generated! -->\n')
        f.write(post)

def build_post(path):
    # Handle Markdown
    source = os.path.join(path, '_main.md')
    target = os.path.join(path, 'index.html')
    if os.path.isfile(source):
        print('Building: %s' % source)
        build_post_markdown(source, target)
    return

def build_all():
    # Process posts
    posts = 'posts'
    for path in os.listdir(posts):
        path = os.path.join(posts, path)
        build_post(path)

def main():
    build_all()
    return

if __name__ == '__main__':
    main()
