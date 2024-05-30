`starmer` started life as a config generator for [Kea DHCP][isc-kea] (sounds like "Keir").

Now, it's not that at all.  The `cmd/` directory contains a series of programs
for Netbox-driven generation of other configs, such as Prometheus HTTP SD
target lists and DNS zone data.

[isc-kea]: https://www.isc.org/kea/

## Building

Have the Go toolchain installed: <https://go.dev/dl/>

The minimum Go version is 1.22.

`go build cmd/<name of utility>` and you will end up with the binary in the
current working directory.

**Note**: the go-netbox library is a bit naughty and needs ~3 GB of free memory
available to compile (on Linux x86-64, at least).  You will probably run out of
memory otherwise.  Thankfully you only have to compile it once and it will then
be reused in future program compilations.
