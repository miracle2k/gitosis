import errno
import logging
import os

from ConfigParser import NoSectionError, NoOptionError

log = logging.getLogger('gitosis.htaccess')

from gitosis import util
from gitosis import access
from gitosis import group
from gitosis import gitdaemon

def htaccess_path(repopath):
    p = os.path.join(repopath, '.htaccess')
    return p

def remove_htaccess(repopath):
    p = htaccess_path(repopath)
    try:
        os.unlink(p)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise

def write_htaccess(repopath, users, groups):
    path = htaccess_path(repopath)
    tmp  = '%s.%d.tmp' % (path, os.getpid())

    f = file(tmp, 'w')
    try:
        ulist = sorted(users)
        if ulist <> []:
            print >>f, 'Require user '+' '.join(ulist)
        glist = sorted(groups)
        if glist <> []:
            print >>f, 'Require group '+' '.join(glist)
        if ulist == [] and glist == []:
            print >>f, 'Order allow,deny'
            print >>f, 'Deny from all'
    finally:
        f.close()

    os.rename(tmp, path)


def gen_htaccess(config):
    table = access.getAccessTable(config)

    for (dirpath, repo, name) in gitdaemon.walk_repos(config):
        (users, groups, all_refs) = access.getAllAccess(config,table,name)

        if '@all' in all_refs:
            log.debug('Allow all for %r', name)
            remove_htaccess(os.path.join(dirpath, repo))
        else:
            write_htaccess(os.path.join(dirpath, repo), users, groups)


def gen_htaccess_if_enabled(config):
    try:
        do_htaccess = config.getboolean('gitosis', 'htaccess')
    except (NoSectionError, NoOptionError):
        do_htaccess = False

    if do_htaccess:
        gen_htaccess(config)

    return do_htaccess

