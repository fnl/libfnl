DIR=`pwd` #"$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
. bin/activate
export PYTHONPATH="$DIR/src"
export PATH="$DIR/scripts":"$PATH"
