ChurchKey
================================================

``churchkey`` is a program tunneling SSH through HTTP proxies with
authentication.

Intro
================================================

``churchkey`` tunnels SSH sessions through HTTP proxies, which means the user
logs into a remote server via an HTTP proxy instead of performing direct access.
It does so by using the ``CONNECT`` request method defined in the HTTP protocol.

The technical details are described in `RFC 2817`_.

Alternative HTTP tunneling programs include Corkscrew_ and Proxytunnel_.

Install
================================================

``churchkey`` contains a single file written in Python 3. Therefore the install
is merely a file download.

Please note that ``churchkey`` doesn't support Python 2 officially. However,
there shouldn't be major difficulty porting it to Python 2.

Usage
================================================

The usage of ``churchkey`` should be very familiar to ``corkscrew`` users:

1.  Create a file ``~/.ssh/proxyauth`` with proxy username and password:

::

    <username>:<password>

2.  Edit ``~/.ssh/config`` as follows:

::

    Host <host>
        HostName <hostname>
        Port <port>
        User <user>
        ProxyCommand churchkey <proxy_host> <proxy_port> %h %p ~/.ssh/proxyauth

3.  Log into remote server using this command:

::

    ssh <host>


Authentication Methods
================================================

``churchkey`` currenctly supports two HTTP authentication methods: Basic_ and
Digest_.


License
================================================

The source code is licensed under the `GNU General Public License v3.0`_.

Copyright (C) 2016 Cyker Way

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


.. _RFC 2817: https://tools.ietf.org/html/rfc2817
.. _Corkscrew: http://agroman.net/corkscrew/
.. _Proxytunnel: http://proxytunnel.sourceforge.net/
.. _Basic: https://en.wikipedia.org/wiki/Basic_access_authentication
.. _Digest: https://en.wikipedia.org/wiki/Digest_access_authentication
.. _GNU General Public License v3.0: https://www.gnu.org/licenses/gpl-3.0.txt
