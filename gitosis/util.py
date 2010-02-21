import errno
import os

from ConfigParser import NoSectionError, NoOptionError

def mkdir(*a, **kw):
    try:
        os.mkdir(*a, **kw)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

def getRepositoryDir(config):
    repositories = os.path.expanduser('~')
    try:
        path = config.get('gitosis', 'repositories')
    except (NoSectionError, NoOptionError):
        repositories = os.path.join(repositories, 'repositories')
    else:
        repositories = os.path.join(repositories, path)
    return repositories

def getGeneratedFilesDir(config):
    try:
        generated = config.get('gitosis', 'generate-files-in')
    except (NoSectionError, NoOptionError):
        generated = os.path.expanduser('~/gitosis')
    return generated

def getSSHAuthorizedKeysPath(config):
    try:
        path = config.get('gitosis', 'ssh-authorized-keys-path')
    except (NoSectionError, NoOptionError):
        path = os.path.expanduser('~/.ssh/authorized_keys')
    return path


def getConfigList(config, section, entry):
    try:
        return config.get(section, entry).split()
    except (NoSectionError, NoOptionError):
        return []


def getConfigDefault(config, specificSection, entry, defaultValue, defaultSection = None):
    try:
        return config.get(specificSection, entry)
    except (NoSectionError, NoOptionError):
        if defaultSection is None:
            return defaultValue

        try:
            return config.get(defaultSection, entry)
        except (NoSectionError, NoOptionError):
            return defaultValue


def toBoolean(cfg, v):
    try:
        return cfg._boolean_states[v.lower()]
    except KeyError:
        raise ValueError, 'Not a boolean: %s' % v

def getConfigDefaultBoolean(config, specificSection, entry, defaultValue, defaultSection = None):
    try:
        return toBoolean(config, config.get(specificSection, entry))
    except (NoSectionError, NoOptionError):
        if defaultSection is None:
            return defaultValue
        try:
            return toBoolean(config, config.get(defaultSection, entry))
        except (NoSectionError, NoOptionError):
            return defaultValue
