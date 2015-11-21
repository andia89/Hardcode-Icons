#!/usr/bin/python3
'''
Author : Bilal Elmoussaoui (bil.elmoussaoui@gmail.com) , Andreas Angerer
Version : 0.1
Licence : GPL
'''

from csv import reader
from gi.repository import Gtk
from os import geteuid, getlogin, listdir, path, chown, getenv, remove
from subprocess import Popen, PIPE, call
from sys import exit
from shutil import copyfile, move
from collections import OrderedDict
try:
    from cairosvg import svg2png
except ImportError:
    exit("You need to install python3-cairosvg to run this script.\nPlease install it and try again. Exiting.")

if geteuid() != 0:
    exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")

db_file = "db.csv"
db_folder = "database/"
userhome = path.expanduser("~" + getlogin())
theme = Gtk.IconTheme.get_default()

fixed_icons = []
reverted_icons = []
script_errors = []

def copy_file(src, dest, overwrite=False):
    """
        Simple copy file function with the possibility to overwrite the file
        Args :
            src(str) : source file
            dest(str) : destination folder
            overwrite(bool) : True to overwrite the file False by default
    """
    if overwrite:
        if path.isfile(dest):
            remove(dest)
        copyfile(src, dest)
    else:
        if not path.isfile(dest):
            copyfile(src, dest)


def get_app_icons(app_name):
    """
        Gets a list of icons of each application
        Args:
            app_name(str): The application name
    """
    if path.isfile(db_folder + app_name):
        f = open(db_folder + app_name)
        r = reader(f, skipinitialspace=True)
        icons = []
        for icon in r:
            if icon != "":
                if len(icon) != 1:
                    icons.append(icon)
                else:
                    icons.extend(icon)
        f.close()
        return icons
    else:
        print("The application " + app_name + " does not exist yet, please report this on GitHub")


def get_apps_informations():
    """
        Read the database file and return a dictionnary with all the informations needed
    """
    db = open(db_file)
    r = reader(db, skipinitialspace=True)
    next(r)
    apps = OrderedDict()
    for app in r:
        app[2] = app[2].replace("{userhome}", userhome).strip()
        if app[2]:
            if path.isdir(app[2]):
                icons = get_app_icons(app[1])
                apps[app[1]] = OrderedDict()
                if icons:
                    apps[app[1]]["name"]   = app[0]
                    apps[app[1]]["path"]   = app[2]
                    apps[app[1]]["icons"]  = icons
                    apps[app[1]]["dbfile"] = app[1]
                else:
                    continue
        else:
            continue
    db.close()
    return apps


def backup(icon, revert=False):
    """
        Backup functions, enables reverting
        Args:
            icon(str) : the original icon name
            revert(bool) : True: revert, False: only backup
    """
    back_file = icon + ".bak"
    if path.isfile(icon):
        if not revert:
            copy_file(icon, back_file)
        elif revert:
            move(back_file, icon)


def reinstall():
    """
        Reverting to the original icons
    """
    apps = get_apps_informations()
    if len(apps) != 0:
        for app in apps:
            app_icons = apps[app]["icons"]
            app_path = apps[app]["path"]
            for icon in app_icons:
                if isinstance(icon, list):
                        revert_icon = icon[0]  #Hardcoded icon to be reverted
                else:
                    revert_icon = icon.strip()
                    try:
                        backup(app_path + revert_icon, revert=True)
                    except:
                        continue
                    if not revert_icon in reverted_icons:
                        print("%s -- reverted" % (revert_icon))
                        reverted_icons.append(revert_icon)


def install():
    """
        Installing the new supported icons
    """
    apps = get_apps_informations()
    if len(apps) != 0:
        for app in apps:
            app_icons = apps[app]["icons"]
            app_path  = apps[app]["path"]
            app_name  = apps[app]["name"]
            for icon in app_icons:
                icon_size = icon[2]
                icon = [item.strip() for item in icon]
                base_icon = path.splitext(icon[0])[0]
                symlink_icon = path.splitext(icon[1])[0]
                if theme.lookup_icon(symlink_icon, int(icon_size), 0):
                    repl_icon = icon[1]
                    symlink_icon = icon[0]
                else:
                    repl_icon = symlink_icon = icon[0]
                extension_orig = path.splitext(symlink_icon)[1]
                theme_icon = theme.lookup_icon(path.basename(base_icon), int(icon_size), 0)
                if theme_icon:
                    filename = theme_icon.get_filename()
                    extension_theme = path.splitext(filename)[1]
                    #catching the unrealistic case that theme is neither svg nor png
                    if extension_theme not in (".png", ".svg"):
                        exit("Theme icons need to be svg or png files other formats are not supported")
                    if symlink_icon:
                        output_icon = apps[app]["path"] + symlink_icon
                    else:
                        output_icon = apps[app]["path"] + repl_icon
                    backup(output_icon)
                    if extension_theme == extension_orig:
                        Popen(["ln", "-sf", filename, output_icon])
                        print("%s -- fixed using %s" % (app_name, path.basename(filename)))
                    elif extension_theme == ".svg" and extension_orig == ".png":
                        try:#Convert the svg file to a png one
                            with open(filename, "r") as content_file:
                                svg = content_file.read()
                            fout = open(output_icon, "wb")
                            svg2png(bytestring=bytes(svg, "UTF-8"), write_to=fout)
                            fout.close()
                            chown(output_icon, int(getenv("SUDO_UID")), int(getenv("SUDO_GID")))
                        except:
                            print("The svg file `" + filename + "` is invalid.")
                            continue
                        #to avoid identical messages
                        if not (filename in fixed_icons):
                            print("%s -- fixed using %s" % (app_name, path.basename(filename)))
                            fixed_icons.append(filename)
                    elif extension_theme == ".png" and extension_orig == ".svg":
                        print("Theme icon is png and hardcoded icon is svg. There is nothing we can do about that :(")
                        continue
                    else:
                        print("Hardcoded file has to be svg or png. Other formats are not supported yet")
                        continue
                    #to avoid identical messages
                    if not (filename in fixed_icons):
                            print("%s -- fixed using %s" % (app_name, path.basename(filename)))
                            fixed_icons.append(filename)
    else:
        exit("No apps to fix! Please report on GitHub if this is not the case")

print("Welcome to the applications hardcoded icons fixer!")
print("1 - Apply")
print("2 - Revert")
try:
    choice  = int(input("Please choose: "))
    if choice == 1:
        print("Applying now..\n")
        install()
    elif choice == 2:
        print("Reverting now..\n")
        reinstall()
    else:
        exit("Please try again")
except ValueError:
    exit("Please choose a valid value")

print("\nDone , Thank you for using the Hardcode-Icons fixer!")
