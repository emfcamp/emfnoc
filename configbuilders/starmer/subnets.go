// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"encoding/json"
	"fmt"
	"net/netip"
)

type Pool struct {
	Start netip.Addr
	End   netip.Addr
}

type DhcpOption struct {
	Name  string `json:"name"`
	Code  int    `json:"code"`
	Data  string `json:"data"`
	Space string `json:"space,omitempty"`
}

type Reservation struct {
	IpAddr netip.Addr `json:"ip-address"`

	HwAddr   string `json:"hw-address,omitempty"`
	Hostname string `json:"hostname,omitempty"`
	Duid     string `json:"duid"`
	FlexId   string `json:"flex-id"`

	NextServer     netip.Addr `json:"next-server,omitempty"`
	ServerHostname string     `json:"server-hostname,omitempty"`
	BootFile       string     `json:"boot-file-name,omitempty"`

	OptionData []DhcpOption `json:"option-data,omitempty"`
}

type Subnet4 struct {
	SubnetCIDR netip.Prefix `json:"subnet"`
	Pools      []Pool       `json:"pools,omitempty"`
	OptionData []DhcpOption `json:"option-data,omitempty"`
}

func (p *Pool) MarshalJSON() ([]byte, error) {
	result := make(map[string]string)
	result["pool"] = fmt.Sprintf("%s - %s", p.Start, p.End)
	return json.Marshal(result)
}

func exampleSubnet() Subnet4 {
	pfx, _ := netip.ParsePrefix("192.0.2.0/25")
	subnet := Subnet4{
		SubnetCIDR: pfx,
		Pools: []Pool{
			{Start: netip.MustParseAddr("192.0.2.5"), End: netip.MustParseAddr("192.0.2.254")},
		},
		OptionData: nil,
	}
	return subnet
}
