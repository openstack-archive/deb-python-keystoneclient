#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import getpass
import hashlib
import logging
import sys

from oslo_utils import encodeutils
from oslo_utils import timeutils
from positional import positional  # noqa
import prettytable
import six

from keystoneclient import exceptions


logger = logging.getLogger(__name__)


# Decorator for cli-args
def arg(*args, **kwargs):
    def _decorator(func):
        # Because of the semantics of decorator composition if we just append
        # to the options list positional options will appear to be backwards.
        func.__dict__.setdefault('arguments', []).insert(0, (args, kwargs))
        return func
    return _decorator


def pretty_choice_list(l):
    return ', '.join("'%s'" % i for i in l)


def print_list(objs, fields, formatters={}, order_by=None):
    pt = prettytable.PrettyTable([f for f in fields],
                                 caching=False, print_empty=False)
    pt.aligns = ['l' for f in fields]

    for o in objs:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](o))
            else:
                field_name = field.lower().replace(' ', '_')
                data = getattr(o, field_name, '')
                if data is None:
                    data = ''
                row.append(data)
        pt.add_row(row)

    if order_by is None:
        order_by = fields[0]
    encoded = encodeutils.safe_encode(pt.get_string(sortby=order_by))
    if six.PY3:
        encoded = encoded.decode()
    print(encoded)


def _word_wrap(string, max_length=0):
    """wrap long strings to be no longer than max_length."""
    if max_length <= 0:
        return string
    return '\n'.join([string[i:i + max_length] for i in
                     range(0, len(string), max_length)])


def print_dict(d, wrap=0):
    """pretty table prints dictionaries.

    Wrap values to max_length wrap if wrap>0
    """
    pt = prettytable.PrettyTable(['Property', 'Value'],
                                 caching=False, print_empty=False)
    pt.aligns = ['l', 'l']
    for (prop, value) in six.iteritems(d):
        if value is None:
            value = ''
        value = _word_wrap(value, max_length=wrap)
        pt.add_row([prop, value])
    encoded = encodeutils.safe_encode(pt.get_string(sortby='Property'))
    if six.PY3:
        encoded = encoded.decode()
    print(encoded)


def find_resource(manager, name_or_id):
    """Helper for the _find_* methods."""

    # first try the entity as a string
    try:
        return manager.get(name_or_id)
    except (exceptions.NotFound):
        pass

    # finally try to find entity by name
    try:
        if isinstance(name_or_id, six.binary_type):
            name_or_id = name_or_id.decode('utf-8', 'strict')
        return manager.find(name=name_or_id)
    except exceptions.NotFound:
        msg = ("No %s with a name or ID of '%s' exists." %
               (manager.resource_class.__name__.lower(), name_or_id))
        raise exceptions.CommandError(msg)
    except exceptions.NoUniqueMatch:
        msg = ("Multiple %s matches found for '%s', use an ID to be more"
               " specific." % (manager.resource_class.__name__.lower(),
                               name_or_id))
        raise exceptions.CommandError(msg)


def unauthenticated(f):
    """Adds 'unauthenticated' attribute to decorated function.

    Usage::

        @unauthenticated
        def mymethod(f):
            ...
    """
    f.unauthenticated = True
    return f


def isunauthenticated(f):
    """Check if function requires authentication.

    Checks to see if the function is marked as not requiring authentication
    with the @unauthenticated decorator.

    Returns True if decorator is set to True, False otherwise.
    """
    return getattr(f, 'unauthenticated', False)


def hash_signed_token(signed_text, mode='md5'):
    hash_ = hashlib.new(mode)
    hash_.update(signed_text)
    return hash_.hexdigest()


def prompt_user_password():
    """Prompt user for a password

    Prompt for a password if stdin is a tty.
    """
    password = None

    # If stdin is a tty, try prompting for the password
    if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
        # Check for Ctl-D
        try:
            password = getpass.getpass('Password: ')
        except EOFError:
            pass

    return password


def prompt_for_password():
    """Prompt user for password if not provided.

    Prompt is used so the password doesn't show up in the
    bash history.
    """
    if not (hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()):
        # nothing to do
        return

    while True:
        try:
            new_passwd = getpass.getpass('New Password: ')
            rep_passwd = getpass.getpass('Repeat New Password: ')
            if new_passwd == rep_passwd:
                return new_passwd
        except EOFError:
            return


_ISO8601_TIME_FORMAT_SUBSECOND = '%Y-%m-%dT%H:%M:%S.%f'
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


def isotime(at=None, subsecond=False):
    """Stringify time in ISO 8601 format."""

    # Python provides a similar instance method for datetime.datetime objects
    # called isoformat(). The format of the strings generated by isoformat()
    # have a couple of problems:
    # 1) The strings generated by isotime are used in tokens and other public
    #    APIs that we can't change without a deprecation period. The strings
    #    generated by isoformat are not the same format, so we can't just
    #    change to it.
    # 2) The strings generated by isoformat do not include the microseconds if
    #    the value happens to be 0. This will likely show up as random failures
    #    as parsers may be written to always expect microseconds, and it will
    #    parse correctly most of the time.

    if not at:
        at = timeutils.utcnow()
    st = at.strftime(_ISO8601_TIME_FORMAT
                     if not subsecond
                     else _ISO8601_TIME_FORMAT_SUBSECOND)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if tz == 'UTC' else tz)
    return st


def strtime(at=None):
    at = at or timeutils.utcnow()
    return at.strftime(timeutils.PERFECT_TIME_FORMAT)
