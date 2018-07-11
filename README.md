Electromagnetic Field - Network configuration
=============================================

All the scripts and configuration that power the EMFCamp network.

Subnet plans and service configuration (DNS, DHCP, Icinga, etc) are all stored in a private Google Spreadsheet, the scripts in the configbuilders folder takes this data and produces local configs on the virtual machines.

Every EMF, Google breaks their API in a backwards-compatible way, and makes the login more and more complicated. It's no longer sufficient to just login with credentials. Here's the procedure for 2018:

First create /etc/emf-gdata.conf 

    [gdata]
    noc_combined=[id of the NOC combined spreadsheet]
    oauth_client_id=[client id of an app]
    oauth_client_secret=client secret of an app]

Then run any generator. It'll provide you a URL to visit in a web browser, login with a user who has access to the spreadsheet. After approving access, paste the token back into the generator and it'll give you another line to add to /etc/emf-gdata.conf. Paste it in and then run the generator again.

Links
-----

Follow us on twitter @emfnoc - http://twitter.com/emfnoc

Presentations
-------------

EMF 2012:
- Slides: https://github.com/emfcamp/emfnoc/blob/master/archives/2012/documents/EMF_2012_Infrastructure_Review.pdf
- Video:

EMF 2014:
- Slides: https://github.com/emfcamp/emfnoc/blob/master/archives/2014/documents/EMF%202014%20network%20presentation.pdf
- Video: https://www.youtube.com/watch?v=H9p3hjRhpyg

EMF 2016:
- Slides: https://github.com/emfcamp/emfnoc/blob/master/archives/2016/documents/EMF_2016_Infrastructure_Review.pdf
- Video: https://www.youtube.com/watch?v=TO8vWj6WYgk

EMF 2018:
- It'll be great.
- You know it.
