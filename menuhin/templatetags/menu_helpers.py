# -*- coding: utf-8 -*-
from classytags.blocks import BlockDefinition, VariableBlockName
from classytags.core import Tag, Options
from classytags.arguments import Argument, Flag
from django import template

register = template.Library()

class IfDepthGreater(Tag):
    name = 'ifdepthgt'
    options = Options(
        Argument('current_node', required=False, resolve=True),
        Argument('context_name', required=False, resolve=False),
        blocks=[
            BlockDefinition('nodelist', 'endifdepthgt')
        ]
    )

    def render_tag(self, context, current_node, context_name, nodelist):
        position_in_loop = context['forloop']['counter0']
        if position_in_loop > 0:
            previous_node = context[context_name][position_in_loop - 1]
            if current_node.depth > previous_node.depth:
                return nodelist.render(context)
        return ''
register.tag(IfDepthGreater)


class IfDepthLess(Tag):
    name = 'ifdepthlt'
    options = Options(
        Argument('current_node', required=False, resolve=True),
        Argument('context_name', required=False, resolve=False),
        blocks=[
            BlockDefinition('nodelist', 'endifdepthlt')
        ]
    )

    def render_tag(self, context, current_node, context_name, nodelist):
        position_in_loop = context['forloop']['counter0']
        if position_in_loop > 0:
            previous_node = context[context_name][position_in_loop - 1]
            if current_node.depth < previous_node.depth:
                return nodelist.render(context)
        return ''
register.tag(IfDepthLess)


class IfDepth(Tag):
    name = 'ifdepth'
    options = Options(
        Flag('deeper', true_values=['>'], false_values=['<']),
        Argument('current_node', required=False, resolve=True),
        Argument('context_name', required=False, resolve=False),
        blocks=[
            BlockDefinition('nodelist', 'endifdepthlt')
        ]
    )

    def render_tag(self, context, deeper, current_node, context_name, nodelist):
        position_in_loop = context['forloop']['counter0']
        if position_in_loop > 0:
            previous_node = context[context_name][position_in_loop - 1]
            if current_node.depth < previous_node.depth:
                return nodelist.render(context)
        return ''
register.tag(IfDepth)
