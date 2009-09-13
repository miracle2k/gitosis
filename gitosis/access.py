import os, logging
from fnmatch import fnmatch

from gitosis import group
from gitosis import util

def pathMatchPatterns(path, repos):
    """
    Check existence of given path against list of path patterns

    The pattern definition is the as fnmatch.fnmatch.
    """
    for repo in repos:
        if fnmatch(path, repo):
            return True
    return False

def haveAccess(config, user, mode, path):
    """
    Map request for write access to allowed path.

    Note for read-only access, the caller should check for write
    access too.

    Returns ``None`` for no access, or a tuple of toplevel directory
    containing repositories and a relative path to the physical repository.
    """
    log = logging.getLogger('gitosis.access.haveAccess')

    log.debug(
        'Access check for %(user)r as %(mode)r on %(path)r...'
        % dict(
        user=user,
        mode=mode,
        path=path,
        ))

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        log.debug(
            'Stripping .git suffix from %(path)r, new value %(basename)r'
            % dict(
            path=path,
            basename=basename,
            ))
        path = basename

    sections = ['group %s' % item for item in
                 group.getMembership(config=config, user=user)]
    sections.insert(0, 'user %s' % user)

    for sectname in sections:
        repos = util.getConfigList(config, sectname, mode)

        mapping = None

        if pathMatchPatterns(path, repos):
            log.debug(
                'Access ok for %(user)r as %(mode)r on %(path)r'
                % dict(
                user=user,
                mode=mode,
                path=path,
                ))
            mapping = path
        else:
            mapping = util.getConfigDefault(config,
                                            sectname,
                                            'map %s %s' % (mode, path),
                                            None)
            if mapping:
                log.debug(
                    'Access ok for %(user)r as %(mode)r on %(path)r=%(mapping)r'
                    % dict(
                    user=user,
                    mode=mode,
                    path=path,
                    mapping=mapping,
                    ))

        if mapping is not None:
            prefix = util.getConfigDefault(config,
                                           sectname,
                                           'repositories',
                                           'repositories',
                                           'gitosis')

            log.debug(
                'Using prefix %(prefix)r for %(path)r'
                % dict(
                prefix=prefix,
                path=mapping,
                ))
            return (prefix, mapping)


def cacheAccess(config, mode, cache):
    """
    Computes access lists for all repositories in one pass.
    """
    for sectname in config.sections():
        GROUP_PREFIX = 'group '
        USER_PREFIX  = 'user '
        REPO_PREFIX  = 'repo '
        if sectname.startswith(USER_PREFIX):
            idx = 0
            name = sectname[len(USER_PREFIX):]
        elif sectname.startswith(GROUP_PREFIX):
            idx = 1
            name = sectname[len(GROUP_PREFIX):]
        elif sectname.startswith(REPO_PREFIX):
            # Single repository: handle owner
            name = sectname[len(REPO_PREFIX):]
            if (mode,name) not in cache:
                cache[mode,name] = (set(),set())

            continue

        else:
            continue

        repos = util.getConfigList(config, sectname, mode)
        for (iname, ivalue) in config.items(sectname):
            if iname.startswith('map %s ' % mode):
                repos.append(ivalue)

        for path in repos:
            if (mode,path) not in cache:
                cache[mode,path] = (set(),set())

            cache[mode,path][idx].add(name)


def listAccess(config, table, mode, path, users, groups):
    """
    List users and groups who can access the path.

    Note for read-only access, the caller should check for write
    access too.
    """

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        path = basename

    if (mode,path) in table:
        (cusers, cgroups) = table[mode,path]
        users.update(cusers)
        groups.update(cgroups)

    if (mode,None) in table:
        (cusers, cgroups) = table[mode,None]
        users.update(cusers)
        groups.update(cgroups)


def getAccessTable(config,modes=['readonly','writable','writeable']):
    """
    A trivial helper that builds ACL table for all repositories
    and given set of modes.
    """
    table = dict()
    for mode in modes:
        cacheAccess(config,mode,table)

    return table


def getAllAccess(config,table,path,modes=['readonly','writable','writeable']):
    """
    Returns access information for a certain repository.
    """
    users = set()
    groups = set()
    for mode in modes:
        listAccess(config,table,mode,path,users,groups)

    all_refs = set(['@'+item for item in groups])
    for grp in groups:
        group.listMembers(config,grp,all_refs)

    return (users, groups, all_refs)
