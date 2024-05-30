// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"context"
	"fmt"

	"github.com/netbox-community/go-netbox/v3"
)

func GetDhcpPrefixes(ctx context.Context, ipam *netbox.IpamAPIService) ([]netbox.Prefix, error) {
	req := ipam.IpamPrefixesList(ctx).Limit(500)

	results := make([]netbox.Prefix, 0)

	paginated, _, err := req.Execute()
	if err != nil {
		return nil, err
	}
	if paginated.GetNext() != "" {
		return nil, fmt.Errorf("Too many results (>%d) - pagination support nonexistent", 500)
	}
	for _, pfx := range paginated.GetResults() {
		val, exists := pfx.GetCustomFields()["dhcp"]
		if exists {
			dhcp, ok := val.(bool)
			if ok && dhcp {
				results = append(results, pfx)
			}
		}
	}
	return results, nil
}
