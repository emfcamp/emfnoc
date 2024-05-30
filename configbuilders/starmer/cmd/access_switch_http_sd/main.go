// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"encoding/json"
	"net/http"

	"github.com/netbox-community/go-netbox/v3"
	"github.com/prometheus/prometheus/discovery/targetgroup"

	"github.com/emfcamp/emfnoc/configbuilders/starmer/cmdlib"
	"github.com/emfcamp/emfnoc/configbuilders/starmer/switchinfo"
)

func main() {
	cl := cmdlib.GetNetboxClient()
	http.HandleFunc("/access-switches", *accessSwitchHttpSD(cl.DcimAPI))
	http.ListenAndServe("0.0.0.0:8232", nil)
}

func accessSwitchHttpSD(dcim *netbox.DcimAPIService) *http.HandlerFunc {
	var handler http.HandlerFunc
	handler = func(resp http.ResponseWriter, req *http.Request) {

		configs := make([]targetgroup.Group, 0)
		sws, err := switchinfo.GetSwitchesWithRoles(req.Context(), dcim, []string{"access-switch", "distribution-switch"})
		if err != nil {
			resp.WriteHeader(500)
			return
		}
		for _, sw := range sws {
			configs = append(configs, *switchinfo.SwitchPromTarget(&sw))
		}

		b, err := json.Marshal(configs)
		if err != nil {
			resp.WriteHeader(500)
			return
		}

		resp.Header().Set("Content-Type", "application/json")
		resp.Write(b)
	}

	return &handler
}
