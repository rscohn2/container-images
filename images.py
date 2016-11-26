from __future__ import print_function

import argparse
import getpass
import jinja2
import os
import re
import subprocess
import sys


def get_proxies():
    '''Pass through proxies to docker container'''
    proxies = ''
    for var in ['http_proxy','https_proxy','no_proxy']:
        if var in os.environ:
            proxies += ' --build-arg %s=%s' % (var,os.environ[var])
    return proxies

class Templates():
    '''singleton to render the templates'''
    def __init__(self):
        loader = jinja2.FileSystemLoader(searchpath = 'tpls')
        env = jinja2.Environment(loader=loader)
        self._readme = env.get_template('tpl.README.md')
        self._dockerfile = env.get_template('tpl.Dockerfile')
        self._post_push = env.get_template('tpl.post_push')

    def render(self, conf):
        name = conf.name()
        with open('configs/%s/README.md' % name,'wb') as fh:
            fh.write(self._readme.render(conf).encode('utf-8'))
        with open('configs/%s/Dockerfile' % name,'wb') as fh:
            fh.write(self._dockerfile.render(conf).encode('utf-8'))
        with open('configs/%s/hooks/post_push' % name,'wb') as fh:
            fh.write(self._post_push.render(conf).encode('utf-8'))

# singleton
templates = Templates()

def parse_name(name):
    pattern = re.compile(r'intelpython(?P<pyver>[23])_(?P<package>.*)')
    match = pattern.match(name)
    return (int(match.group('pyver')),match.group('package'))

class Conf(dict):
    '''Docker image configuration'''
    def __init__(self,pyver=None,package=None,name=None):
        if name:
            (pyver,package) = parse_name(name)
        self['pyver'] = pyver
        self['package'] = package
        self['release'] = '2017.0.1'

    def name(self):
        return 'intelpython%d_%s' % (self['pyver'],self['package'])

    def tag(self):
        return '%s/%s' % (getpass.getuser(),self.name())

    def gen(self):
        templates.render(self)

    def build(self):
        cmd = 'docker build %s -t %s --file configs/%s/Dockerfile configs/%s' % (get_proxies(),self.tag(),self.name(),self.name())
        print('    ',cmd)
        subprocess.check_call(cmd, shell=True)

    def test(self):
        cmd = 'docker run -t %s python -c 1' % self.tag()
        print('    ',cmd)
        subprocess.check_call(cmd, shell=True)

# Add new configurations here
all_confs = [Conf(2,'core'),
             Conf(2,'full'),
             Conf(3,'core'),
             Conf(3,'full')
]

def main():
    conf_names = [conf.name() for conf in all_confs]
    parser = argparse.ArgumentParser(description='generate the configurations for docker images')
    parser.add_argument('--gen',
                        action='store_true',
                        help='Generate Dockerfile and README.md')
    parser.add_argument('--build',
                        action='store_true',
                        help='Build docker image')
    parser.add_argument('--test',
                        action='store_true',
                        help='Test docker image')
    parser.add_argument('conf',
                        choices=['all'] + conf_names,
                        nargs='*', 
                        help='list of confs to generate')
    args = parser.parse_args()
    if args.conf[0] == 'all':
        args.conf = conf_names

    for n in args.conf:
        print('Processing:',n)
        c = Conf(name=n)
        if args.gen | args.build | args.test:
            print('  gen')
            c.gen()
        if args.build | args.test:
            print('  build')
            c.build()
        if args.test:
            print('  test')
            c.test()
            

main()
