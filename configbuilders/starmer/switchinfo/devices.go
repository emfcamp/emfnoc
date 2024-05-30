package switchinfo

import (
	"context"
	"fmt"
	"net/netip"

	"github.com/netbox-community/go-netbox/v3"
	"github.com/paulmach/orb"
)

type Switch struct {
	Name string
	MgmtIP netip.Addr
	Loc Location
	Status netbox.DeviceStatus
}

func GetSwitchesWithRoles(ctx context.Context, dcim *netbox.DcimAPIService, roles []string) ([]Switch, error) {
	req := dcim.DcimDevicesList(ctx).Role(roles).Limit(500)

	results := make([]Switch, 0)

	paginated, _, err := req.Execute()
	if err != nil {
		return nil, err
	}
	if paginated.GetNext() != "" {
		return nil, fmt.Errorf("Too many results (>%d) - pagination support nonexistent", 500)
	}

	for _, dev := range paginated.GetResults() {
		nloc := dev.GetLocation()
		loc := Location{
			nloc.Name,
			orb.Point{52, 0},
		}
	
		results = append(results, Switch{
			Name: dev.GetName(),
			MgmtIP: netip.MustParsePrefix(dev.GetPrimaryIp4().Address).Addr(),
			Loc: loc,
			Status: dev.GetStatus(),
		})
		
	}

	return results, nil
}
