# /etc/puppet/modules/emfhosts/manifests/init.pp

class emfhosts {

# noc servers

  host { 'puppet.emf.camp':      host_aliases => 'puppet',       ip => '78.158.87.4' }
  host { 'pbx.emf.camp':         ip => '78.158.87.20' }
  host { 'jmp.emf.camp':         ip => '78.158.87.21' }
  host { 'services1.emf.camp':   ip => '78.158.87.11' }
  host { 'services2.emf.camp':   ip => '78.158.87.12' }

# non-noc servers

  host { 'schedule.emf.camp':    ip => '78.158.87.198' }
  host { 'phone.emf.camp':       ip => '78.158.87.196' }
  host { 'content.emf.camp':     ip => '78.158.87.197' }
  host { 'lights.emf.camp':      ip => '78.158.87.199' }

  host {'SWDIST-DC.emf.camp':    host_aliases => 'SWDIST-DC',    ip => '94.45.255.130' }
  host {'SWDIST-G1.emf.camp':    host_aliases => 'SWDIST-G1',    ip => '94.45.255.131' }
  host {'SWDIST-C2.emf.camp':    host_aliases => 'SWDIST-C2',    ip => '94.45.255.132' }
  host {'SWDK-E2.emf.camp':      host_aliases => 'SWDK-E2',      ip => '94.45.255.133' }
  host {'SWDK-E1.emf.camp':      host_aliases => 'SWDK-E1',      ip => '94.45.255.134' }
  host {'SWKIDS.emf.camp':       host_aliases => 'SWKIDS',       ip => '94.45.255.135' }
  host {'SWDK-D2.emf.camp':      host_aliases => 'SWDK-D2',      ip => '94.45.255.136' }
  host {'SWDK-D1.emf.camp':      host_aliases => 'SWDK-D1',      ip => '94.45.255.137' }
  host {'SWDK-C1.emf.camp':      host_aliases => 'SWDK-C1',      ip => '94.45.255.138' }
  host {'SWDK-C2.emf.camp':      host_aliases => 'SWDK-C2',      ip => '94.45.255.139' }
  host {'SWDK-C3.emf.camp':      host_aliases => 'SWDK-C3',      ip => '94.45.255.140' }
  host {'SWDK-B1.emf.camp':      host_aliases => 'SWDK-B1',      ip => '94.45.255.141' }
  host {'SWDK-A1.emf.camp':      host_aliases => 'SWDK-A1',      ip => '94.45.255.142' }
  host {'SWDK-A2.emf.camp':      host_aliases => 'SWDK-A2',      ip => '94.45.255.143' }
  host {'SWDK-B2.emf.camp':      host_aliases => 'SWDK-B2',      ip => '94.45.255.144' }
  host {'SWDK-H1.emf.camp':      host_aliases => 'SWDK-H1',      ip => '94.45.255.145' }
  host {'SWDK-J1.emf.camp':      host_aliases => 'SWDK-J1',      ip => '94.45.255.146' }
  host {'SWDK-H2.emf.camp':      host_aliases => 'SWDK-H2',      ip => '94.45.255.147' }
  host {'SWDK-J2.emf.camp':      host_aliases => 'SWDK-J2',      ip => '94.45.255.148' }
  host {'SWDK-G1.emf.camp':      host_aliases => 'SWDK-G1',      ip => '94.45.255.149' }
  host {'SWDK-G2.emf.camp':      host_aliases => 'SWDK-G2',      ip => '94.45.255.150' }
  host {'SWWORKSHOP-1.emf.camp': host_aliases => 'SWWORKSHOP-1', ip => '94.45.255.151' }
  host {'SWWORKSHOP-2.emf.camp': host_aliases => 'SWWORKSHOP-2', ip => '94.45.255.152' }
  host {'SWWORKSHOP-3.emf.camp': host_aliases => 'SWWORKSHOP-3', ip => '94.45.255.153' }
  host {'SWWORKSHOP-4.emf.camp': host_aliases => 'SWWORKSHOP-4', ip => '94.45.255.154' }
  host {'SWSTAGE-B.emf.camp':    host_aliases => 'SWSTAGE-B',    ip => '94.45.255.155' }
  host {'SWHQ.emf.camp':         host_aliases => 'SWHQ',         ip => '94.45.255.156' }
  host {'SWNOC.emf.camp':        host_aliases => 'SWNOC',        ip => '94.45.255.157' }
  host {'SWDK-X1.emf.camp':      host_aliases => 'SWDK-X1',      ip => '94.45.255.158' }
  host {'SWDK-S1.emf.camp':      host_aliases => 'SWDK-S1',      ip => '94.45.255.159' }
  host {'SWDK-S2.emf.camp':      host_aliases => 'SWDK-S2',      ip => '94.45.255.160' }
  host {'SWDK-U1.emf.camp':      host_aliases => 'SWDK-U1',      ip => '94.45.255.161' }
  host {'SWSTAGE-A.emf.camp':    host_aliases => 'SWSTAGE-A',    ip => '94.45.255.162' }
  host {'SWDK-U2.emf.camp':      host_aliases => 'SWDK-U2',      ip => '94.45.255.163' }
  host {'SWBAR.emf.camp':        host_aliases => 'SWBAR',        ip => '94.45.255.164' }
  host {'SWSTAGE-C.emf.camp':    host_aliases => 'SWSTAGE-C',    ip => '94.45.255.165' }
  host {'SWLOUNGE.emf.camp':     host_aliases => 'SWLOUNGE',     ip => '94.45.255.166' }
  host {'SWINFODESK.emf.camp':   host_aliases => 'SWINFODESK',   ip => '94.45.255.167' }
  host {'SWEMFM.emf.camp':       host_aliases => 'SWEMFM',       ip => '94.45.255.168' }
  host {'DOCKLANDS.emf.camp':    host_aliases => 'DOCKLANDS',    ip => '78.158.87.113' }
  host {'BLETCHLEY.emf.camp':    host_aliases => 'BLETCHLEY',    ip => '78.158.87.114' }
  host {'SWCORE.emf.camp':       host_aliases => 'SWCORE',       ip => '78.158.87.115' }

  host {'SWDIST_DC.emf.camp':    host_aliases => 'SWDIST_DC',    ensure => 'absent' }
  host {'SWDIST_G1.emf.camp':    host_aliases => 'SWDIST_G1',    ensure => 'absent' }
  host {'SWDIST_C2.emf.camp':    host_aliases => 'SWDIST_C2',    ensure => 'absent' }
  host {'SWDK_E2.emf.camp':      host_aliases => 'SWDK_E2',      ensure => 'absent' }
  host {'SWDK_E1.emf.camp':      host_aliases => 'SWDK_E1',      ensure => 'absent' }
  host {'SWDK_D2.emf.camp':      host_aliases => 'SWDK_D2',      ensure => 'absent' }
  host {'SWDK_D1.emf.camp':      host_aliases => 'SWDK_D1',      ensure => 'absent' }
  host {'SWDK_C1.emf.camp':      host_aliases => 'SWDK_C1',      ensure => 'absent' }
  host {'SWDK_C2.emf.camp':      host_aliases => 'SWDK_C2',      ensure => 'absent' }
  host {'SWDK_C3.emf.camp':      host_aliases => 'SWDK_C3',      ensure => 'absent' }
  host {'SWDK_B1.emf.camp':      host_aliases => 'SWDK_B1',      ensure => 'absent' }
  host {'SWDK_A1.emf.camp':      host_aliases => 'SWDK_A1',      ensure => 'absent' }
  host {'SWDK_A2.emf.camp':      host_aliases => 'SWDK_A2',      ensure => 'absent' }
  host {'SWDK_B2.emf.camp':      host_aliases => 'SWDK_B2',      ensure => 'absent' }
  host {'SWDK_H1.emf.camp':      host_aliases => 'SWDK_H1',      ensure => 'absent' }
  host {'SWDK_J1.emf.camp':      host_aliases => 'SWDK_J1',      ensure => 'absent' }
  host {'SWDK_H2.emf.camp':      host_aliases => 'SWDK_H2',      ensure => 'absent' }
  host {'SWDK_J2.emf.camp':      host_aliases => 'SWDK_J2',      ensure => 'absent' }
  host {'SWDK_G1.emf.camp':      host_aliases => 'SWDK_G1',      ensure => 'absent' }
  host {'SWDK_G2.emf.camp':      host_aliases => 'SWDK_G2',      ensure => 'absent' }
  host {'SWWORKSHOP_1.emf.camp': host_aliases => 'SWWORKSHOP_1', ensure => 'absent' }
  host {'SWWORKSHOP_2.emf.camp': host_aliases => 'SWWORKSHOP_2', ensure => 'absent' }
  host {'SWWORKSHOP_3.emf.camp': host_aliases => 'SWWORKSHOP_3', ensure => 'absent' }
  host {'SWWORKSHOP_4.emf.camp': host_aliases => 'SWWORKSHOP_4', ensure => 'absent' }
  host {'SWSTAGE_B.emf.camp':    host_aliases => 'SWSTAGE_B',    ensure => 'absent' }
  host {'SWDK_X1.emf.camp':      host_aliases => 'SWDK_X1',      ensure => 'absent' }
  host {'SWDK_S1.emf.camp':      host_aliases => 'SWDK_S1',      ensure => 'absent' }
  host {'SWDK_S2.emf.camp':      host_aliases => 'SWDK_S2',      ensure => 'absent' }
  host {'SWDK_U1.emf.camp':      host_aliases => 'SWDK_U1',      ensure => 'absent' }
  host {'SWSTAGE_A.emf.camp':    host_aliases => 'SWSTAGE_A',    ensure => 'absent' }
  host {'SWDK_U2.emf.camp':      host_aliases => 'SWDK_U2',      ensure => 'absent' }
  host {'SWSTAGE_C.emf.camp':    host_aliases => 'SWSTAGE_C',    ensure => 'absent' }

}
