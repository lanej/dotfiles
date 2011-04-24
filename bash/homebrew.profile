PATH="/Users/jhansen/Developer/bin:/Users/jhansen/Developer/share/npm/bin:/Users/jhansen/Developer/sbin:$PATH"; export PATH
MANPATH="/Users/jhansen/Developer/share/man:$MANPATH"; export MANPATH
CFLAGS="-I/Users/jhansen/Developer/include"; export CFLAGS
CPPFLAGS="-I/Users/jhansen/Developer/include"; export CPPFLAGS
CXXFLAGS="-I/Users/jhansen/Developer/include"; export CXXFLAGS
LDFLAGS="-L/Users/jhansen/Developer/lib"; export LDFLAGS
NODE_PATH="/Users/jhansen/Developer/lib/node"; export NODE_PATH

export CONFIGURE_ARGS="--with-cflags='$CFLAGS' --with-ldflags='$LDFLAGS'"
