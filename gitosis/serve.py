"""
Enforce git-shell to only serve allowed by access control policy.
directory. The client should refer to them without any extra directory
prefix. Repository names are forced to match ALLOW_RE.
"""

import logging

import sys, os, re

from ConfigParser import NoSectionError, NoOptionError

from gitosis import access
from gitosis import repository
from gitosis import gitweb
from gitosis import gitdaemon
from gitosis import htaccess
from gitosis import app
from gitosis import util
from gitosis import group

log = logging.getLogger('gitosis.serve')

ALLOW_RE = re.compile("^'/*(?P<path>[a-zA-Z0-9][a-zA-Z0-9@._-]*(/[a-zA-Z0-9][a-zA-Z0-9@._-]*)*)'$")

COMMANDS_READONLY = [
    'git-upload-pack',
    'git upload-pack',
    ]

COMMANDS_WRITE = [
    'git-receive-pack',
    'git receive-pack',
    ]

class ServingError(Exception):
    """Serving error"""

    def __str__(self):
        return '%s' % self.__doc__

class CommandMayNotContainNewlineError(ServingError):
    """Command may not contain newline"""

class UnknownCommandError(ServingError):
    """Unknown command denied"""

class UnsafeArgumentsError(ServingError):
    """Arguments to command look dangerous"""

class AccessDenied(ServingError):
    """Access denied to repository"""

class WriteAccessDenied(AccessDenied):
    """Repository write access denied"""

class ReadAccessDenied(AccessDenied):
    """Repository read access denied"""

def auto_init_repo(cfg,topdir,repopath):
    # create leading directories
    p = topdir

    assert repopath.endswith('.git'), 'must have .git extension'
    newdirmode = util.getConfigDefault(cfg,
                                       'repo %s' % repopath[:-4],
                                       'dirmode',
                                       None,
                                       'defaults')
    if newdirmode is not None:
        newdirmode = int(newdirmode, 8)
    else:
        newdirmode = 0750

    for segment in repopath.split(os.sep)[:-1]:
        p = os.path.join(p, segment)
        util.mkdir(p, newdirmode)

    fullpath = os.path.join(topdir, repopath)

    # init using a custom template, if required
    try:
        template = cfg.get('gitosis', 'init-template')
        repository.init(path=fullpath, template=template, mode=newdirmode)
    except (NoSectionError, NoOptionError):
        pass

    repository.init(path=fullpath, mode=newdirmode)

def path_from_args(args):
    match = ALLOW_RE.match(args)
    if match is None:
        raise UnsafeArgumentsError()

    return match.group('path')

def path_for_write(cfg, user, path):
    # write access is always sufficient
    newpath = access.haveAccess(
        config=cfg,
        user=user,
        mode='writable',
        path=path)

    if newpath is None:
        # didn't have write access; try once more with the popular
        # misspelling
        newpath = access.haveAccess(
            config=cfg,
            user=user,
            mode='writeable',
            path=path)
        if newpath is not None:
            log.warning(
                'Repository %r config has typo "writeable", '
                +'should be "writable"',
                path,
                )

    return newpath

def construct_path(newpath):
    (topdir, relpath) = newpath
    assert not relpath.endswith('.git'), \
           'git extension should have been stripped: %r' % relpath
    repopath = '%s.git' % relpath

    return (topdir, repopath)

def serve(
    cfg,
    user,
    command,
    ):
    if '\n' in command:
        raise CommandMayNotContainNewlineError()

    try:
        verb, args = command.split(None, 1)
    except ValueError:
        # all known "git-foo" commands take one argument; improve
        # if/when needed
        raise UnknownCommandError()

    if verb == 'git':
        try:
            subverb, args = args.split(None, 1)
        except ValueError:
            # all known "git foo" commands take one argument; improve
            # if/when needed
            raise UnknownCommandError()
        verb = '%s %s' % (verb, subverb)
    elif verb == 'cvs':
        try:
            args, server = args.split(None, 1)
        except:
            raise UnknownCommandError()
        if server != 'server':
            raise UnknownCommandError()

        path = path_from_args(args)

        newpath = path_for_write(cfg=cfg, user=user, path=path)
        if newpath is None:
            raise WriteAccessDenied()

        (topdir, repopath) = construct_path(newpath)

        # Put the repository and base path in the environment
        repos_dir = util.getRepositoryDir(cfg)
        fullpath = os.path.join(repos_dir, repopath)
        os.environ['GIT_CVSSERVER_BASE_PATH'] = repos_dir
        os.environ['GIT_CVSSERVER_ROOTS'] = fullpath

        # Put the user's information in the environment
        try:
            section = 'user %s' % user
            name = cfg.get(section, 'name')
            email = cfg.get(section, 'email')
        except:
            log.error('Missing name or email for user "%s"' % user)
            raise WriteAccessDenied()
        os.environ['GIT_AUTHOR_NAME'] = name
        os.environ['GIT_AUTHOR_EMAIL'] = email

        return 'cvs server'

    if (verb not in COMMANDS_WRITE
        and verb not in COMMANDS_READONLY):
        raise UnknownCommandError()

    path = path_from_args(args)

    # write access is always sufficient
    newpath = path_for_write(
        cfg=cfg,
        user=user,
        path=path)

    if newpath is None:
        # didn't have write access

        newpath = access.haveAccess(
            config=cfg,
            user=user,
            mode='readonly',
            path=path)

        if newpath is None:
            raise ReadAccessDenied()

        if verb in COMMANDS_WRITE:
            # didn't have write access and tried to write
            raise WriteAccessDenied()

    (topdir, repopath) = construct_path(newpath)
    fullpath = os.path.join(topdir, repopath)
    if not os.path.exists(fullpath):
        # it doesn't exist on the filesystem, but the configuration
        # refers to it, we're serving a write request, and the user is
        # authorized to do that: create the repository on the fly
        auto_init_repo(cfg,topdir,repopath)
        gitweb.set_descriptions(
            config=cfg,
            )
        generated = util.getGeneratedFilesDir(config=cfg)
        gitweb.generate_project_list(
            config=cfg,
            path=os.path.join(generated, 'projects.list'),
            )
        gitdaemon.set_export_ok(
            config=cfg,
            )
        htaccess.gen_htaccess_if_enabled(
            config=cfg,
            )

    # put the verb back together with the new path
    newcmd = "%(verb)s '%(path)s'" % dict(
        verb=verb,
        path=fullpath,
        )
    return newcmd

class Main(app.App):
    def create_parser(self):
        parser = super(Main, self).create_parser()
        parser.set_usage('%prog [OPTS] USER')
        parser.set_description(
            'Allow restricted git operations under DIR')
        return parser

    def handle_args(self, parser, cfg, options, args):
        try:
            (user,) = args
        except ValueError:
            parser.error('Missing argument USER.')

        main_log = logging.getLogger('gitosis.serve.main')
        os.umask(0022)

        cmd = os.environ.get('SSH_ORIGINAL_COMMAND', None)
        if cmd is None:
            main_log.error('Need SSH_ORIGINAL_COMMAND in environment.')
            sys.exit(1)

        main_log.debug('Got command %(cmd)r' % dict(
            cmd=cmd,
            ))

        os.chdir(os.path.expanduser('~'))

        try:
            newcmd = serve(
                cfg=cfg,
                user=user,
                command=cmd,
                )
        except ServingError, e:
            main_log.error('%s', e)
            sys.exit(1)

        command = ['git', 'shell', '-c', newcmd]
        main_log.info('Serving %s', str(command))
        os.execvp('git', command)
        main_log.error('Cannot execute git-shell.')
        sys.exit(1)
