from nose.tools import eq_ as eq, assert_raises

from ConfigParser import RawConfigParser
from cStringIO import StringIO

from gitosis import group

def test_no_emptyConfig():
    cfg = RawConfigParser()
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_no_emptyGroup():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_no_notListed():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_simple():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_leading():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'jdoe wsmith')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_trailing():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_middle():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith jdoe danny')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_one():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith @smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'danny jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_one_ordering():
    cfg = RawConfigParser()
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'danny jdoe')
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith @smackers')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_three():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith @smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'danny @snackers')
    cfg.add_section('group snackers')
    cfg.set('group snackers', 'members', '@whackers foo')
    cfg.add_section('group whackers')
    cfg.set('group whackers', 'members', 'jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'whackers')
    eq(gen.next(), 'snackers')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_junk():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', '@notexist @smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_loop():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', '@smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', '@hackers jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_no_recurse_loop():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', '@smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', '@hackers')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_groupList_multiple():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.add_section('group all')
    cfg.set('group all', 'readonly', 'zap')
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'a b c @bar')
    cfg.add_section('group bar')
    cfg.set('group bar', 'members', 'c d')
    cfg.add_section('group baz')
    cfg.set('group baz', 'members', '@all')
    got = StringIO()
    group.generate_group_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
foo: a b c d
bar: c d
baz: 
''')
