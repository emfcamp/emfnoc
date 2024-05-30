package switchinfo

import (
	_ "embed"

	prom "github.com/prometheus/common/model"
	"github.com/prometheus/prometheus/discovery/targetgroup"
)

func SwitchPromTarget(s *Switch) *targetgroup.Group {
	group := &targetgroup.Group{}

	group.Targets = make([]prom.LabelSet, 0)
	group.Targets = append(group.Targets, prom.LabelSet{
		prom.AddressLabel: prom.LabelValue(s.MgmtIP.String()),
	})

	group.Labels = prom.LabelSet{
		"device_name":   prom.LabelValue(s.Name),
		"location_name": prom.LabelValue(s.Loc.Name),
		"status":        prom.LabelValue(*s.Status.Value),
		"device_type":   prom.LabelValue(s.DeviceType.Slug),
	}

	return group
}
