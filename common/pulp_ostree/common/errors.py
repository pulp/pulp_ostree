from gettext import gettext as _

from pulp.common.error_codes import Error


OST0001 = Error('OST0001',
                _('Create local repository at: %(path)s failed.  Reason: %(reason)s'),
                ['path', 'reason'])

OST0002 = Error('OST0002',
                _('Pulling remote branch: %(branch)s failed.  Reason: %(reason)s'),
                ['branch', 'reason'])

OST0003 = Error('OST0003',
                _('Delete remote: %(id)s failed.  Reason: %(reason)s'),
                ['id', 'reason'])
