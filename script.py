#!/usr/bin/python3
'''
Author : Bilal Elmoussaoui (bil.elmoussaoui@gmail.com) , Andreas Angerer
Version : 0.1 Beta
Licence : GPL
'''

from csv import reader
from gi.repository import Gtk
from os import environ, geteuid, getlogin, listdir, path, makedirs, chown, getenv, symlink, remove
from subprocess import Popen, PIPE, call
from sys import exit
from shutil import rmtree, copyfile, move
from hashlib import md5
try:
    from cairosvg import svg2png
except ImportError:
    exit("You need to install python3-cairosvg to run this script.\nPlease install it and try again. Exiting.")

if geteuid() != 0:
    exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")

db_file = "db.csv"
db_folder = "database"
userhome = path.expanduser("~" + getlogin())
theme = Gtk.IconTheme.get_default()

fixed_icons = []
reverted_icons = []
script_errors = [] 

# Creates a list of subdirectories
def get_subdirs(directory):
    """
        Return a list of subdirectories, used in replace_dropbox_dir
        @directory : String, the path of the directory 
    """
    if path.isdir(directory):
        dirs = listdir(directory)
        dirs.sort()
        sub_dirs = []
        for sub_dir in sub_dirs:
            if path.isdir(directory + "/" + sub_dir):
                sub_dirs.append(sub_dir)
        return sub_dirs
    else:
        return None


def copy_file(src, dest, overwrite=False):
    """
        Simple copy file function with the possibility to overwrite the file
        @src : String, the source file
        @dest : String, the destination folder 
        @overwrite : Boolean, to overwrite the file 
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
        get a list of icons in /database/applicationname of each application 
        @app_name : String, the application name
    """
    if path.isfile(db_folder + "/" + app_name):
        f = open(db_folder + "/" + app_name)
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
        return None

def get_apps_informations():
    """
        Read the database file and return a dictionnary with all the informations needed
    """
    db = open(db_file)
    r = reader(db, skipinitialspace=True)
    apps = {}
    for app in r:
        app[1] = app[1].replace("{userhome}", userhome).strip()
        if app[1]:
            if path.isdir(app[1] + "/"):
                icons = get_app_icons(app[0])
                if icons:
                        apps[app[0]] = {"path": app[1], "icons": icons}
                else:
                    continue
        else:
            continue
    db.close()
    return apps


def backup(icon, revert=False):
    """
        A backup fonction, used to make reverting to the original icons possible
        @icon : String, the original icon name 
        @revert : Boolean, possibility to revert the icons later 
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
            folder = apps[app]["path"]
            for icon in app_icons:
                if isinstance(icon, list):
                        revert_icon = icon[0]  #Hardcoded icon to be reverted
                else:
                    revert_icon = icon.strip()
                    try:
                        backup(folder + "/" + revert_icon, revert=True)
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
            for icon in app_icons:
                if isinstance(icon, list):
                    icon = [item.strip() for item in icon] 
                    base_icon = path.splitext(icon[0])[0]
                    if theme.lookup_icon(base_icon, default_icon_size, 0):
                        repl_icon = symlink_icon = icon[0]
                    else:
                        symlink_icon = icon[0]  #Hardcoded icon to be replaced
                        repl_icon = icon[1]  #Theme Icon that will replace hardcoded icon
                else:
                    symlink_icon = repl_icon = icon.strip()
                base_icon = path.splitext(repl_icon)[0]
                extension_orig = path.splitext(symlink_icon)[1]
                theme_icon = theme.lookup_icon(base_icon, default_icon_size, 0)
                if theme_icon:
                    filename = theme_icon.get_filename()
                    extension_theme = path.splitext(filename)[1]
                     #catching the unrealistic case that theme is neither svg nor png
                    if extension_theme not in (".png", ".svg"):
                        exit("Theme icons need to be svg or png files other formats are not supported")
                    if not script:
                        if symlink_icon:
                            output_icon = apps[app]["path"] + "/" + symlink_icon
                        else:
                            output_icon = apps[app]["path"] + "/" + repl_icon
                        backup(output_icon)
                        if extension_theme == extension_orig:
                            Popen(["ln", "-sf", filename, output_icon])
                            print("%s -- fixed using %s" % (app, filename))
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
                                print("%s -- fixed using %s" % (app, filename))
                                fixed_icons.append(filename)
                        elif extension_theme == ".png" and extension_orig == ".svg":
                            print("Theme icon is png and hardcoded icon is svg. There is nothing we can do about that :(")
                            continue
                        else:
                            print("Hardcoded file has to be svg or png. Other formats are not supported yet")
                            continue
                    #to avoid identical messages
                    if not (filename in fixed_icons):
                        if not err:
                            print("%s -- fixed using %s" % (app, filename))
                            fixed_icons.append(filename)
                        else: 
                            if not err in script_errors:
                                script_errors.append(err)
                                err = err.decode("utf-8")
                                err = "\n".join(["\t" + e for e in err.split("\n")])
                                print("fixing %s failed with error:\n%s"%(app, err))
    else:
        exit("No apps to fix! Please report on GitHub if this is not the case")

if detect_de() in ("pantheon", "xfce"):
    default_icon_size = 24

print("Welcome to the tray icons hardcoder fixer! \n")
print("1 - Install \n")
print("2 - Reinstall \n")
try:
    choice  = int(input("Please choose: "))
    if choice == 1:
        print("Installing now..\n")
        install() 
    elif choice == 2:
        print("Reinstalling now..\n")
        reinstall()
    else:   
        exit("Please try again")
except ValueError:
    exit("Please choose a valid value")

print("\nDone , Thank you for using the Hardcode-Tray fixer!")
