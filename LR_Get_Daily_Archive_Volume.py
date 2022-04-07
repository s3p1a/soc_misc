import os
from collections import defaultdict

ARCHIVE_PATH = 'D:\LogRhythmArchives\Inactive'

# https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
def get_size(start_path = ARCHIVE_PATH):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

# https://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
ARCHIVE_SUBFOLDERS = [ f.path for f in os.scandir(ARCHIVE_PATH) if f.is_dir() ]
DAILY_COUNTS = defaultdict(float)
for subfolder in ARCHIVE_SUBFOLDERS:
    folderName = subfolder.split('\\')[-1]
    folderDate = folderName.split('_')[0]
    folderBytes = get_size(subfolder)
    folderGigabytes = folderBytes / (1024 * 1024 * 1024)
    DAILY_COUNTS[folderDate] += folderGigabytes

for (k,v) in DAILY_COUNTS.items():
    print(f'{k}, {v}')
