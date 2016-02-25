from gettext import gettext as _

from pulp.common.error_codes import Error


OST0001 = Error('OST0001',
                _('Create local repository at: %(path)s failed.  Reason: %(reason)s'),
                ['path', 'reason'])

OST0002 = Error('OST0002',
                _('Pulling remote refs failed.  Reason: %(reason)s'),
                ['reason'])

OST0003 = Error('OST0003',
                _('Delete remote: %(id)s failed.  Reason: %(reason)s'),
                ['id', 'reason'])
OST0004 = Error('OST0004',
                _('Feed URL not specified'),
                [])
