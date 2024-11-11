#!/bin/bash

# test-large-file.sh: Test the upload(create / update) and download of a large(2GB) file
# Usage: test-large-file.sh <project_id> <storage_provider>

set -e

export PROJECT_ID=$1
export STORAGE_PROVIDER=$2

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <project_id> <storage_provider>"
    exit 1
fi
if [ -z "$STORAGE_PROVIDER" ]; then
    echo "Usage: $0 <project_id> <storage_provider>"
    exit 1
fi

# Set the client timeout to 10 minutes
export OSF_CLIENT_TIMEOUT=600

# OSF_DEBUG: Set to --debug to enable debug output

# Create a large file
dd if=/dev/urandom of=large-file-2g bs=1M count=2000
md5sum large-file-2g

# Upload the large file
osf -p ${PROJECT_ID} --base-url https://api.rdm.nii.ac.jp/v2/ ${OSF_DEBUG} upload large-file-2g ${STORAGE_PROVIDER}/large-file-2g

# Download the large file
osf -p ${PROJECT_ID} --base-url https://api.rdm.nii.ac.jp/v2/ ${OSF_DEBUG} fetch ${STORAGE_PROVIDER}/large-file-2g large-file-2g.downloaded

# Check the downloaded file
md5sum large-file-2g.downloaded
rm large-file-2g.downloaded

# Create a large file(for overwrite)
dd if=/dev/urandom of=large-file-2g bs=1M count=2000
md5sum large-file-2g

# Overwrite the large file
osf -p ${PROJECT_ID} --base-url https://api.rdm.nii.ac.jp/v2/ ${OSF_DEBUG} upload -U large-file-2g ${STORAGE_PROVIDER}/large-file-2g

# Download the large file
osf -p ${PROJECT_ID} --base-url https://api.rdm.nii.ac.jp/v2/ ${OSF_DEBUG} fetch ${STORAGE_PROVIDER}/large-file-2g large-file-2g.downloaded

# Check the downloaded file
md5sum large-file-2g.downloaded

# Remove the large file
osf -p ${PROJECT_ID} --base-url https://api.rdm.nii.ac.jp/v2/ ${OSF_DEBUG} remove ${STORAGE_PROVIDER}/large-file-2g

# Clean up
rm large-file-2g large-file-2g.downloaded
