// SPDX-License-Identifier: AGPL-3.0-only

package switchinfo

import "github.com/paulmach/orb"

type Location struct {
	Name string
	WGS84 orb.Point
}
