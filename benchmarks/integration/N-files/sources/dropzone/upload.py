FILES = {}
def upload(owner, data):
    i = len(FILES) + 1
    FILES[i] = {'owner': owner, 'data': data}
    return i
def delete(i):
    FILES.pop(i)
