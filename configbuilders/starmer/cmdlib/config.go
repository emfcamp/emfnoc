package cmdlib

import (
	"fmt"

	"github.com/netbox-community/go-netbox/v3"
	"github.com/spf13/viper"
)

func GetNetboxClient() (*netbox.APIClient) {
	viper.SetDefault("NetboxURL", "http://localhost:8080")
	viper.SetDefault("AuthToken", "")
	viper.SetEnvPrefix("starmer")
	viper.AutomaticEnv()

	cl := netbox.NewAPIClientFor(viper.GetString("NetboxURL"), viper.GetString("AuthToken"))
	config := cl.GetConfig()
	config.UserAgent = fmt.Sprintf("starmer %s (+https://github.com/emfcamp/emfnoc/tree/master/configbuilders/starmer)", config.UserAgent)

	return cl
}
