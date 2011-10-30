# -*- coding: utf-8 -*-

import os
from django import template

register = template.Library()

@register.filter
def basename(path):
    return path.split('/')[-1]
