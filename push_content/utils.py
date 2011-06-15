from urlparse import urlparse

from push_content.models import ItemToPush


def join_url_to_directory(url, directory):
    ends_with = url.endswith('/')
    starts_with = directory.endswith('/')

    if ends_with and starts_with:
        return ''.join((url, directory[1:]))

    if ((ends_with and not starts_with) or
        (not ends_with and starts_with)):
        return ''.join((url, directory))

    if not ends_with and not starts_with:
        return ''.join((url, '/', directory))

    raise Exception('Unhandled case')


class URL:
    """Represents an url with information extracted so that it's easly
    accessible"""

    def __init__(self, url):
        self.url = url
        parsed = urlparse(url)
        self.scheme = parsed.scheme
        self.path = parsed.path
        self.params = parsed.params
        self.query = parsed.query
        self.fragment = parsed.fragment

        if '@' in parsed.netloc:
            login_password, self.domain = parsed.netloc.split('@')
            self.login, self.password = login_password.split(':')
        else:
            self.domain = parsed.netloc
            self.login = self.password = None

        if ':' in self.domain:
            self.domain, self.port = self.domain.split(':')
        else:
            self.port = None


def duplicate_row(rule_name, instance):
    """Checks if there is already is a row like this one."""
    app_label = instance._meta.app_label
    model = instance._meta.module_name
    name = instance._meta.verbose_name
    id = instance.id

    query = ItemToPush.objects.filter(rule_name=rule_name,
                                      status=ItemToPush.STATUS.NEW,
                                      content_type__app_label=app_label,
                                      content_type__model=model,
                                      content_type__name=name,
                                      object_id=id)
    count = query.count()

    return count > 0
