import os
def preview(path):
    with open(path, 'rb') as f:
        return f.read(64)
