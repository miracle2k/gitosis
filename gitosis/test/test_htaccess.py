from nose.tools import eq_ as eq

import os
from ConfigParser import RawConfigParser

from gitosis import htaccess
from gitosis.test.util import maketemp, writeFile, readFile

def exported(path,cont):
    assert os.path.isdir(path)
    p = htaccess.htaccess_path(path)
    if cont == None:
        assert not os.path.exists(p)
    else:
        assert os.path.exists(p)
        rcont = readFile(p)
        eq(rcont, cont)

def test_htaccess_export_ok_repo_missing():
    # configured but not created yet; before first push
    tmp = maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'yes')
    htaccess.gen_htaccess(config=cfg)
    assert not os.path.exists(os.path.join(tmp, 'foo'))
    assert not os.path.exists(os.path.join(tmp, 'foo.git'))


def test_htaccess_export_ok_allowed_already():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(htaccess.htaccess_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('user jdoe')
    cfg.set('user jdoe', 'readonly', 'foo')
    htaccess.gen_htaccess(config=cfg)
    exported(path, '''\
Require user jdoe
''')

def test_htaccess_export_ok_all():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(htaccess.htaccess_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group all')
    cfg.set('group all', 'readonly', 'foo')
    htaccess.gen_htaccess(config=cfg)
    exported(path, None)

def test_htaccess_export_ok_subdirs():
    tmp = maketemp()
    foo = os.path.join(tmp, 'foo')
    os.mkdir(foo)
    path = os.path.join(foo, 'bar.git')
    os.mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group some')
    cfg.set('group some', 'writable', 'foo/bar')
    cfg.add_section('user jdoe')
    cfg.set('user jdoe', 'readonly', 'foo/bar')
    htaccess.gen_htaccess(config=cfg)
    exported(path, '''\
Require user jdoe
Require group some
''')

def test_htaccess_export_ok_denied_even_not_configured():
    # repositories not mentioned in config also get touched; this is
    # to avoid security trouble, otherwise we might expose (or
    # continue to expose) old repositories removed from config
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(htaccess.htaccess_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    htaccess.gen_htaccess(config=cfg)
    exported(path, '''\
Order allow,deny
Deny from all
''')

def test_htaccess_disabled():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(htaccess.htaccess_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    eq(htaccess.gen_htaccess_if_enabled(config=cfg),False)
    exported(path, '')
