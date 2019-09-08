#!/usr/bin/python3.6
from datetime import datetime
import magic
from os import listdir
from os.path import isfile, join, getmtime
from PIL import Image
from PIL.ExifTags import TAGS
from shutil import copy2
import sys

COUNTS = {
    'metadata_invalid': 0,
    'metadata_valid': 0,
    'movies': 0,
    'photos': 0,
    'processed': 0
}
SORTED_PATH = '/mnt/shared/exif/sorted'  # Directory where sorted files will go.
SRC_PHOTOS_PATH = '/mnt/shared/exif/photos'  # Directory of source photo files.
UNTAGGED_PATH = '/mnt/shared/exif/untagged'  # Directory where files that aren't EXIF tagged will go.


# Returns a dict of EXIF metadata.
def get_exif(fn):
    ret = {}
    i = Image.open(fn)
    info = i._getexif()
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
    return ret


# Copies files to a new directory, sorted by EXIF create date and named in sequential order, like IMG_xxxx. This naming
# convention is suited for storage on Apple iOS devices.
def sort_files(files_x_metadata):
    counter = int('0000')

    for file in sorted(files_x_metadata, key=lambda k: k['exif_timestamp']):
        file_type = magic.from_file(file['full_path'], mime=True)
        if file_type.lower() == 'image/jpeg':
            extension = 'jpg'
        elif file_type.lower() == 'video/quicktime':
            extension = 'mov'

        new_filepath = join(SORTED_PATH, 'IMG_{:04d}.{}'.format(counter, extension))
        print('Copying to {}'.format(new_filepath))
        copy2(file['full_path'], new_filepath)
        counter += 1


if __name__ == '__main__':

    count_exif_valid = 0
    count_movies = 0
    count_no_metadata = 0
    count_processed = 0

    photos_x_metadata = []
    videos_x_metadata = []
    for file in listdir(SRC_PHOTOS_PATH):
        full_path = join(SRC_PHOTOS_PATH, file)
        if isfile(full_path):
            count_processed += 1
            try:
                exif = get_exif(full_path)
                photos_x_metadata.append(
                    {
                        'full_path': full_path,
                        'exif_timestamp': exif['DateTimeOriginal'],
                        'flags': ['ts_mismatch'] if exif['DateTimeOriginal'] != exif['DateTimeDigitized'] else [],
                        'sorted_path': ''
                    }
                )

                count_exif_valid += 1
            except OSError as e:  # If the file isn't an image file, this will get thrown.
                if 'cannot identify image file' in str(e):
                    if '.mov' in str(e).lower():
                        print('Movie file found: {}'.format(full_path))
                        videos_x_metadata.append(
                            {
                                'full_path': full_path,
                                'exif_timestamp': datetime.fromtimestamp(getmtime(full_path)).strftime('%Y:%m:%d %H:%M:%S'),
                                'flags': 'moviefile',
                                'sorted_path': ''
                            }
                        )
                        count_movies += 1
            except KeyError as e:  # If no EXIF data is found but the file is a JPEG, this will get thrown.
                print('No exif metadata found, using file metadata: {}'.format(full_path))
                photos_x_metadata.append(
                    {
                        'full_path': full_path,
                        'exif_timestamp': datetime.fromtimestamp(getmtime(full_path)).strftime('%Y:%m:%d %H:%M:%S'),
                        'flags': 'filemtime',
                        'sorted_path': ''
                    }
                )
                count_no_metadata += 1
            except AttributeError as e:  # If the file is of an unsupported image file type.
                print('Unsupported filetype: {}'.format(full_path))
                copy2(full_path, join(UNTAGGED_PATH, file))
                count_no_metadata += 1

    sort_files(photos_x_metadata)
    sort_files(videos_x_metadata)

    for file in photos_x_metadata:
        if file['flags'] == 'ts_mismatch':
            print('Timestamp mismatch on file {}'.format(file['full_path']))
    print('Processed: {}\nMovie Files: {}\nValid Metadata: {}\nInvalid Metadata: {}'.format(
        count_processed, count_movies, count_exif_valid, count_no_metadata
    ))
