import shutil
def cleanup_temp_dir(path):
    shutil.rmtree(str(path), ignore_errors=True)
