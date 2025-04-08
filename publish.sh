
#!/bin/bash

# Check if an argument was provided
if [ -z "$1" ]; then
  echo "Usage: ./publish.sh [test|prod]"
  exit 1
fi

python update_readme.py

# Choose where to publish

if [ "$1" = "prod" ]; then
  flit publish --repository pypi
else
  flit publish --repository testpypi
fi