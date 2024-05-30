// SPDX-License-Identifier: AGPL-3.0-only

package dns

import (
	"math"
	"regexp"

	"github.com/miekg/dns"

	"github.com/emfcamp/emfnoc/configbuilders/starmer/switchinfo"
)

const (
	ARCSECOND_PER_DEGREE = 3600
	CENTIMETRES_PER_METRE = 100
	ALTITUDE_ZERO_BASE_METRES = 100_000

	EASTNOR_ALTITUDE_M = 120  // roughly middle
	EASTNOR_ALTITUDE_ERRORBAR_M = 20
)

func SiteLoc(name string, lat, lon, radius float64) *dns.LOC {
	hdr := dns.RR_Header{
		Name: name,
		Rrtype: dns.TypeLOC,
		Class: dns.ClassINET,
		Ttl: 3600,
	}
	rec := &dns.LOC{
		Hdr: hdr,
		Version: 0,
		Size: packSizePrecision(radius * 2),
		HorizPre: packSizePrecision(10),
		VertPre: packSizePrecision(EASTNOR_ALTITUDE_ERRORBAR_M),
		Latitude: packWGS84Coord(lat),
		Longitude: packWGS84Coord(lon),
		Altitude: packAltitude(EASTNOR_ALTITUDE_M),
	}
	return rec
}

func SwitchLOCs(switches []switchinfo.Location) []dns.LOC {
	records := make([]dns.LOC, 0)
	for _, sw := range switches {
		rec := SiteLoc(formatDnsName(sw.Name), sw.WGS84.Lat(), sw.WGS84.Lon(), 10)
		records = append(records, *rec)
	}
	return records
}

func formatDnsName(name string) string {
	nonDnsLetters := regexp.MustCompile("[^A-Za-z0-9_-]")
	return nonDnsLetters.ReplaceAllLiteralString(name, "-")
}

func packSizePrecision(metres float64) uint8 {
	centimetres := metres * 100
	var mantissa, exponent float64
	var bMant, bExp uint8
	exponent = math.Log10(centimetres)
	if exponent < 0 {
		// Less than a centimetre!
		return 0x10
	}
	if exponent > 0x9 {
		// Maxed out
		return 0x99
	}
	bExp = uint8(math.Floor(exponent))
	mantissa = centimetres / math.Pow10(int(bExp))
	if mantissa > 0x9 {
		panic(mantissa)
	}
	bMant = uint8(math.Floor(mantissa))
	return ((bMant << 4) & 0xf0 | (bExp & 0xf))
}

func packWGS84Coord(coord float64) uint32 {
	// RFC 1876:
	// > expressed as a 32-bit integer, most significant octet first (network
	// > standard byte order), in thousandths of a second of arc,
	//
	// and in the case of LONGITUDE:
	// > rounded away from the prime meridian.
	//
	// Other points from the RFC:
	// - 2^31 (== 0x8000_0000) represents the equator or prime meridian.
	// - Positive numbers are Northwards and Eastwards (i.e. usual sign
	//   convention).
	return 0x8000_0000 + uint32(math.Ceil(coord * ARCSECOND_PER_DEGREE * 1000))
}

func packAltitude(altMetres float64) uint32 {
	// RFC 1876:
	// > expressed as a 32-bit integer, most significant octet first (network
	// > standard byte order), in centimeters, from a base of 100,000m below the
	// > WGS 84 reference spheroid used by GPS
	return uint32((altMetres + ALTITUDE_ZERO_BASE_METRES) * CENTIMETRES_PER_METRE)
}
