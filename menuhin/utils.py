# -*- coding: utf-8 -*-
from menuhin.models import MenuHandler

def get_menu(key):
    menu_registry = MenuHandler().load_menus()
    try:
        menu = menu_registry.menus[key]
        if menu.nodes is None or menu.tree is None:
            menu.build()
        return menu
    except KeyError:
        return None

def get_all_menus():
    menu_registry = MenuHandler().load_menus()
    for key in menu_registry.menus.keys():
        menu = menu_registry.menus[key]
        if menu.nodes is None or menu.tree is None:
            menu.build()
    return menu_registry.menus
