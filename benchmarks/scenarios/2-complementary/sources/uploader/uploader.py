"""Uploader: store files and list them (illustrative)."""
MAX_BYTES = 10 * 1024 * 1024  # uploads over 10 MB are rejected

def upload(store, owner_id, filename, data):
    if len(data) > MAX_BYTES:
        raise ValueError("file too large")
    return store.save(owner_id=owner_id, name=filename, size=len(data), data=data)

def list_files(store, owner_id):
    return store.list(owner_id=owner_id)

def delete_file(store, owner_id, file_id):
    return store.delete(owner_id=owner_id, file_id=file_id)
