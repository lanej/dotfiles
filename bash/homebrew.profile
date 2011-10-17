PATH="/Users/jlane/Developer/bin:/Users/jlane/Developer/share/npm/bin:/Users/jlane/Developer/sbin:$PATH"; export PATH
MANPATH="/Users/jlane/Developer/share/man:$MANPATH"; export MANPATH
CFLAGS="-I/Users/jlane/Developer/include"; export CFLAGS
CPPFLAGS="-I/Users/jlane/Developer/include"; export CPPFLAGS
CXXFLAGS="-I/Users/jlane/Developer/include"; export CXXFLAGS
LDFLAGS="-L/Users/jlane/Developer/lib"; export LDFLAGS
NODE_PATH="/Users/jlane/Developer/lib/node"; export NODE_PATH

export CONFIGURE_ARGS="--with-cflags='$CFLAGS' --with-ldflags='$LDFLAGS'"
