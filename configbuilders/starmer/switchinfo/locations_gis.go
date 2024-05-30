// SPDX-License-Identifier: AGPL-3.0-only

package switchinfo

import (
	"database/sql"
	"fmt"

	_ "github.com/lib/pq"
	// "github.com/miekg/dns"

	"github.com/paulmach/orb/encoding/wkb"
)

func GetLocationsFromPostGIS(dsn string) ([]Location, error) {
	q := "select switch, ST_AsBinary(ST_Transform(wkb_geometry, 4326)) from site_plan where layer = 'NOC ... Switch' and passive is null;"

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, fmt.Errorf("While opening DB connection: %w", err)
	}
	defer db.Close()

	rows, err := db.Query(q)
	if err != nil {
		return nil, fmt.Errorf("While reading switch DB: %w", err)
	}

	switches := make([]Location, 0)

	for rows.Next() {
		sw := &Location{}
		rows.Scan(&sw.Name, wkb.Scanner(&sw.WGS84))
		switches = append(switches, *sw)
	}

	return switches, nil
}
