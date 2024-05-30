package main

import (
	"context"
	"fmt"
	"log"

	"github.com/emfcamp/emfnoc/configbuilders/starmer/cmdlib"
	"github.com/emfcamp/emfnoc/configbuilders/starmer/switchinfo"
	"github.com/miekg/dns"
)

const zone string = "net.emf.camp."

func main() {
	cl := cmdlib.GetNetboxClient()
	switches, err := switchinfo.GetSwitchesWithRoles(context.TODO(), cl.DcimAPI, []string{"access-switch", "distribution-switch"}, []string{})

	if err != nil {
		log.Fatalf("Error getting access switches: %s", err)
	}

	for _, sw := range switches {
		rr := makeRecord(sw.Name, "A", sw.MgmtIP.String())
		fmt.Println(rr.String())

		if sw.Loc.Name != "" {
			rr = makeRecord("sw-"+sw.Loc.Name, "CNAME", fmt.Sprintf("%s.%s", sw.Name, zone))
			fmt.Println(rr.String())
		}
	}
}

func makeRecord(label string, typ string, target string) dns.RR {
	record := fmt.Sprintf("%s.%s %s %s", label, zone, typ, target)
	rr, err := dns.NewRR(record)
	if err != nil {
		log.Fatalf("Error in dns.NewRR for %s: %s", label, err)
	}
	return rr
}
