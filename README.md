# churchkey

a tool tunneling ssh over http proxy;

churchkey tunnels ssh sessions through http proxy, so that users can log into
remote server via http proxy if direct access is not working; churchkey uses
http *connect* method and only works with http proxies supporting this method;

churchkey supports two http authentication methods: [basic] and [digest];

technical details are described in [rfc 2817];

alternative projects include [corkscrew] and [proxytunnel];

## install

install via pip:

    pip install churchkey

## usage

1.  create a file `~/.ssh/proxyauth` with proxy username and password:

        <username>:<password>

2.  edit `~/.ssh/config` as follows:

        Host {host}
            HostName {hostname}
            Port {port}
            User {user}
            ProxyCommand churchkey {proxy_host} {proxy_port} %h %p ~/.ssh/proxyauth

3.  log into remote server as usual:

        ssh {host}

## license

Copyright (C) 2016-2018 Cyker Way

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

[rfc 2817]: https://tools.ietf.org/html/rfc2817
[basic]: https://en.wikipedia.org/wiki/Basic_access_authentication
[digest]: https://en.wikipedia.org/wiki/Digest_access_authentication
[corkscrew]: http://agroman.net/corkscrew/
[proxytunnel]: http://proxytunnel.sourceforge.net/

