PATH="/Users/jlane/bin:/Users/jlane/share/npm/bin:/Users/jlane/sbin:$PATH"; export PATH
MANPATH="/Users/jlane/share/man:$MANPATH"; export MANPATH
CFLAGS="-I/Users/jlane/include"; export CFLAGS
CPPFLAGS="-I/Users/jlane/include"; export CPPFLAGS
CXXFLAGS="-I/Users/jlane/include"; export CXXFLAGS
LDFLAGS="-L/Users/jlane/lib"; export LDFLAGS
NODE_PATH="/Users/jlane/lib/node"; export NODE_PATH

export CONFIGURE_ARGS="--with-cflags='$CFLAGS' --with-ldflags='$LDFLAGS'"
