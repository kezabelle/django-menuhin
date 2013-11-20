# -*- coding: utf-8 -*-
from classytags.blocks import BlockDefinition, VariableBlockName
from classytags.core import Tag, Options
from classytags.arguments import Argument, Flag
from django import template

register = template.Library()
#
# class IfDepthGreater(Tag):
#     name = 'ifdepthgt'
#     options = Options(
#         Argument('current_node', required=False, resolve=True),
#         Argument('context_name', required=False, resolve=False),
#         blocks=[
#             BlockDefinition('nodelist', 'endifdepthgt')
#         ]
#     )
#
#     def render_tag(self, context, current_node, context_name, nodelist):
#         position_in_loop = context['forloop']['counter0']
#         if position_in_loop > 0:
#             previous_node = context[context_name][position_in_loop - 1]
#             if current_node.depth > previous_node.depth:
#                 # context[context_name]._last_seen =
#                 return nodelist.render(context)
#         return ''
# register.tag(IfDepthGreater)
#
#
# class IfDepthLess(Tag):
#     name = 'ifdepthlt'
#     options = Options(
#         Argument('current_node', required=False, resolve=True),
#         Argument('context_name', required=False, resolve=False),
#         blocks=[
#             BlockDefinition('nodelist', 'endifdepthlt')
#         ]
#     )
#
#     def render_tag(self, context, current_node, context_name, nodelist):
#         position_in_loop = context['forloop']['counter0']
#         # import pdb; pdb.set_trace()
#         if position_in_loop > 0:
#             previous_node = context[context_name][position_in_loop - 1]
#             if current_node.depth < previous_node.depth:
#                 return nodelist.render(context)
#         return ''
# register.tag(IfDepthLess)
#


class DepthHandler(Tag):
    name = 'depth'
    options = Options(
        Argument('current_node', required=True, resolve=True),
        Argument('context_name', required=False, resolve=False),
        blocks=[
            ('deeper', 'no_change'),
            ('less', 'go_deeper'),
            ('enddepth', 'go_shallower'),
        ]
    )

    def render_tag(self, context, current_node, context_name, **kwargs):
        if 'forloop' not in context or context_name not in context:
            return ''

        position_in_loop = context['forloop']['counter0']
        if position_in_loop < 1:
            context['_previous_node'] = current_node
        previous_node = context['_previous_node']

        if current_node.depth > previous_node.depth:
            difference = current_node.depth - previous_node.depth
            result = kwargs.pop('go_deeper').render(context).strip() * difference

        elif current_node.depth < previous_node.depth:
            difference = previous_node.depth - current_node.depth
            result = kwargs.pop('go_shallower').render(context).strip() * difference

        elif current_node.depth == previous_node.depth:
            difference = 0
            result = kwargs.pop('no_change').render(context).strip()

        # pop it onto the context secretly, and then tidy up afterwards
        context['_previous_node'] = current_node
        # if context['forloop']['last'] == True:
        #     import pdb; pdb.set_trace()
        #     del context['_previous_node']
        # print current_node.title, ' ... ', result, difference
        return result

register.tag(DepthHandler)
