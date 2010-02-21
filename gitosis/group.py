import os, logging
from gitosis import util

def _getMembership(config, user, seen):
    log = logging.getLogger('gitosis.group.getMembership')

    for section in config.sections():
        GROUP_PREFIX = 'group '
        if not section.startswith(GROUP_PREFIX):
            continue
        group = section[len(GROUP_PREFIX):]
        if group in seen:
            continue

        members = util.getConfigList(config, section, 'members')

        # @all is the only group where membership needs to be
        # bootstrapped like this, anything else gets started from the
        # username itself
        if (user in members
            or '@all' in members):
            log.debug('found %(user)r in %(group)r' % dict(
                user=user,
                group=group,
                ))
            seen.add(group)
            yield group

            for member_of in _getMembership(
                config, '@%s' % group, seen,
                ):
                yield member_of


def getMembership(config, user):
    """
    Generate groups ``user`` is member of, according to ``config``

    :type config: RawConfigParser
    :type user: str
    :param _seen: internal use only
    """

    seen = set()
    for member_of in _getMembership(config, user, seen):
        yield member_of

    # everyone is always a member of group "all"
    yield 'all'


def listMembers(config, group, mset):
    """
    Generate a list of members of a group

    :type config: RawConfigParser
    :type group: str
    :param mset: Set of members to amend
    """

    if group <> 'all':
        members = util.getConfigList(config, 'group %s' % group, 'members')

        for user in members:
            mset.add(user)
            if user.startswith('@'):
                listMembers(config, user[1:], mset)


def generate_group_list_fp(config, fp):
    """
    Generate group list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param fp: file to write group list to
    :type fp: file
    """
    for section in config.sections():
        GROUP_PREFIX = 'group '
        if not section.startswith(GROUP_PREFIX):
            continue
        group = section[len(GROUP_PREFIX):]
        if group == 'all':
            continue

        items = set()
        listMembers(config, group, items)

        users = filter(lambda u: not u.startswith('@'), items)
        line = group + ': ' + ' '.join(sorted(users))
        print >>fp, line


def generate_group_list(config, path):
    """
    Generate group list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param path: path to write group list to
    :type path: str
    """
    tmp = '%s.%d.tmp' % (path, os.getpid())

    f = file(tmp, 'w')
    try:
        generate_group_list_fp(config=config, fp=f)
    finally:
        f.close()

    os.rename(tmp, path)
