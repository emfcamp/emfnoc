// SPDX-License-Identifier: AGPL-3.0-only

package switchinfo

import (
	"context"
	"fmt"

	"github.com/netbox-community/go-netbox/v3"
	"github.com/paulmach/orb"
)

func GetLocationsFromNetbox(ctx context.Context, dcim *netbox.DcimAPIService) ([]Location, error) {
	req := dcim.DcimLocationsList(ctx).Limit(500)

	paginated, _, err := req.Execute()
	if err != nil {
		return nil, err
	}
	if paginated.GetNext() != "" {
		return nil, fmt.Errorf("Too many results (>%d) - pagination support nonexistent", 500)
	}

	switches := make([]Location, 0)

	for _, loc := range paginated.GetResults() {
		cfs := loc.GetCustomFields()
		lat, okLat := cfs["latitude"]
		lon, okLon := cfs["longitude"]
		if !(okLat && okLon) {
			continue
		}

		latF, okLat := lat.(float64)
		lonF, okLon := lon.(float64)
		if !(okLat && okLon) {
			continue
		}

		sw := &Location{
			Name: loc.GetName(),
			WGS84: orb.Point{lonF, latF},
		}
		switches = append(switches, *sw)
	}

	return switches, nil
}
