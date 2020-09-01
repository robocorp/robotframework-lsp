import os


def copytree_dst_exists(src, dst, symlinks=False, ignore=None):
    """
    Same as shutil.copytree but the target directory already exists.
    """
    import shutil

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)
